import asyncio
import civitai.models
import common.helper as helper
import json
import os
import re
import requests
import zipfile

from .cache import TrioCache
from .model import TrioModel, TrioModelType
from .template import TrioTemplate
from PIL import Image
from common.exception import DroppyBotException
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from enum import IntEnum
from io import BytesIO
from prodict import Prodict
from shared import CogBase, cwd
from typing import Optional, Union


class TrioResourceType(IntEnum):
    ANY = 0
    MODEL = 1
    TEMPLATE = 2
    CACHE = 3


TrioResource = Union[TrioModel, TrioTemplate, TrioCache]


class TrioResourceManager:
    """
    Backend for managing trio resources

    Should not process any discord related actions here
    """

    def __init__(self, config: Prodict):
        self.config = config

        self.available_query = {
            TrioResourceType.MODEL: self.get_model,
            TrioResourceType.TEMPLATE: self.get_template,
            TrioResourceType.CACHE: self.get_cache,
        }
        self.trio_models: list[TrioModel] = self.load_trio_models()
        self.trio_templates: list[TrioTemplate] = self.load_trio_templates()
        self.trio_caches: list[TrioCache] = self.load_trio_cache()

        self.invalidate_cache()

    def load_trio_models(self):
        model_path = os.path.join(cwd, self.config.trio.model_path)
        trio_models = []
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    for m in json.load(f):
                        trio_models.append(TrioModel(**m))
            except Exception:
                trio_models = []
        return trio_models

    def save_trio_models(self):
        model_path = os.path.join(cwd, self.config.trio.model_path)
        with open(model_path, "w", encoding="utf-8") as f:
            json.dump(
                [m.__dict__ for m in self.trio_models],
                f,
                indent=4,
                ensure_ascii=False,
            )

    def load_trio_templates(self):
        trio_templates = []
        template_path = os.path.join(cwd, self.config.trio.template_path)
        if os.path.exists(template_path):
            try:
                with open(template_path, "rb") as f:
                    trio_templates = [TrioTemplate(**t) for t in json.load(f)]
            except Exception:
                trio_templates = []
        return trio_templates

    def save_trio_templates(self):
        template_path = os.path.join(cwd, self.config.trio.template_path)
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(
                [t.__dict__ for t in self.trio_templates],
                f,
                indent=4,
                ensure_ascii=False,
            )

    def load_trio_cache(self):
        cache_storage = os.path.join(cwd, self.config.trio.cache.storage)
        if not os.path.exists(cache_storage):
            os.makedirs(cache_storage)

        trio_cache = []
        cache_path = os.path.join(cwd, self.config.trio.cache.path)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    trio_cache = [TrioCache(**c) for c in json.load(f)]
            except Exception:
                trio_cache = []
        return trio_cache

    def save_trio_cache(self):
        cache_path = os.path.join(cwd, self.config.trio.cache.path)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                [c.__dict__ for c in self.trio_cache],
                f,
                indent=4,
                ensure_ascii=False,
            )

    def invalidate_cache(self):
        """
        Remove any outdated cache from cache storage
        """

        retention = timedelta(days=self.config.trio.cache.retention)

        validated = []
        for root, _, files in os.walk(
            os.path.join(cwd, self.config.trio.cache.storage)
        ):
            for f in files:
                file_path = os.path.join(root, f)
                valid = False
                for artifact in self.user_artifacts:
                    if artifact.timestamp in f:
                        creation = datetime.fromtimestamp(os.path.getctime(file_path))
                        if datetime.now() - creation < retention:
                            validated.append(artifact)
                            valid = True
                if not valid:
                    os.remove(file_path)

        validated = sorted(validated, key=lambda a: a.timestamp)
        self.user_artifacts = validated
        self.save_user_artifacts()

    def get_cache_path(self, timestamp: str):
        """
        Get full path of specific timestamp
        """
        return os.path.join(
            cwd,
            self.config.trio.cache.storage,
            f"{timestamp}.{self.config.trio.cache.output}",
        )

    def get_cache_artifact(self, cache: TrioCache):
        """
        Get a trio cache's artifact, if present
        """

        if cache is None:
            return None

        artifact = None
        cache_path = self.get_cache_path(cache.timestamp)
        try:
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    artifact = BytesIO(f.read())
        except:
            pass
        return artifact

    @helper.sanitized
    def get_resource(
        self, query: str, *, type: TrioResourceType = TrioResourceType.ANY
    ) -> Optional[TrioResource]:
        """
        Query a trio resource by a name, index, or urn
        """

        for t, q in self.available_query.items():
            if type == t:
                return q(query)
        return next([q(query) for q in self.available_query.values()], None)

    def get_model(self, query: str):
        """
        Query a trio model by name, index, or urn
        """

        model = None
        if query.isnumeric() and int(query) <= len(self.trio_models):
            model = self.trio_models[int(query) - 1]
        else:
            model = helper.first(
                self.trio_models,
                lambda m: helper.iequal(m.name, query) or helper.iequal(m.urn, query),
            )
        return model

    def get_template(self, query: str):
        """
        Query a trio template by name or index
        """

        template = None

        if query.isnumeric() and int(query) <= len(self.user_templates):
            template = self.trio_templates[int(query) - 1]
        else:
            template = helper.first_iequal(self.trio_templates, "name", query)
        return template

    def get_cache(self, query: str):
        """
        Query a trio cache by timestamp
        """

        return helper.first_iequal(self.trio_caches, "timestamp", query)

    def add_resource(self, name: str, resource: TrioResource):
        """
        Add a trio resource
        """
