import asyncio
import civitai.models
import common.helper as helper
import discord
import json
import os
import re
import requests
import zipfile

from PIL import Image
from datetime import datetime, timedelta, UTC
from discord.ext import commands
from io import BytesIO
from common.exception import DroppyBotException
from modules.trio.resource.manager import TrioResourceManager
from modules.trio.resource.cache import TrioArtifact
from modules.trio.resource.model import TrioModel, TrioModelType
from modules.trio.resource.template import TrioTemplate
from modules.trio.trioview import TrioControlView, TrioJobView
from prodict import Prodict
from shared import CogBase, cwd


class TrioHandler(CogBase, commands.Cog):

    def __init__(self):
        self.resource = TrioResourceManager(self.config)

    def get_models(self, model_type: TrioModelType):
        return [m for m in self.trio_models if m.model == model_type]

    def sanitized_parameters(self, parameter: str):
        details = {}
        for param in parameter.split(self.config.trio.delimiter.pack):
            param = param.strip()
            if param.isspace() or param == "" or ":" not in param:
                continue
            if param.endswith(self.config.trio.delimiter.parameter):
                param = param[:-1]
            pack = param.split(":")
            details[pack[0].strip()] = ":".join(pack[1:])
        return Prodict.from_dict(details)

    def fetch_cache(self, artifact: TrioArtifact):
        cache_path = self.get_cache_path(artifact.cache)
        try:
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    return BytesIO(f.read())
        except:
            pass
        return None

    def write_cache(self, buffer: list, cache: str):
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, image in enumerate(buffer):
                if image is not None:
                    raw, seed = image
                    sanitized_buf = BytesIO()
                    self.del_image_info(raw).save(
                        sanitized_buf, self.config.trio.output_type
                    )
                    z.writestr(
                        self.get_image_name(i + 1, str(seed)), sanitized_buf.getvalue()
                    )
        buf.seek(0)
        if buf.getbuffer().nbytes > 0:
            cache_path = self.get_cache_path(cache)
            with open(cache_path, "wb") as f:
                f.write(buf.read())

    def create_input_model(self, template: TrioTemplate, prompt: str):
        return {
            "model": template.base_model,
            "params": {
                "prompt": template.base_prompt
                + self.config.trio.delimiter.parameter
                + prompt,
                "negativePrompt": template.negative_prompt,
                "scheduler": self.config.trio.sampler,
                "steps": int(template.steps),
                "cfgScale": template.guidance,
                "width": int(self.config.trio.dimension.width),
                "height": int(self.config.trio.dimension.height),
                "seed": -1,
                "clipSkip": 2,
            },
            "quantity": int(self.config.trio.concurrent_job_max),
            "additionalNetworks": {
                m: {"type": "Lora", "strength": s}
                for m, s in template.add_models.items()
            },
        }

    def get_image_name(self, index: int, appendix: str | None = None):
        name = f"image_{index}"
        if appendix is not None:
            name += f"_{appendix}"
        extension = f".{self.config.trio.output_type}"
        return name + extension

    def get_image_seed(self, buffer):
        image = Image.open(BytesIO(buffer))
        exif = image.info["exif"].decode("utf-16be", "ignore")
        seed = re.search(r"Seed: (\d+)", exif)
        if seed:
            return int(seed.group(1))
        return -1

    def del_image_info(self, buffer):
        image = Image.open(BytesIO(buffer))
        sanitized = Image.new(image.mode, image.size)
        sanitized.putdata(list(image.getdata()))
        return sanitized

    async def validate_model_type(self, ctx: discord.Message, model_type: str):
        try:
            parse = TrioModelType[model_type.upper()]
        except Exception:
            await ctx.edit(
                embed=self.as_embed(
                    f"invalid model type specified `{model_type.upper()}`\n"
                    + "model inputs are **`CKPT` `LORA` `VAE`**",
                    ctx.author,
                ),
            )
            return None
        return parse

    async def expect_parameters(
        self,
        ctx: discord.Message,
        pack: list,
        parameter_string,
        delimiter: str = None,
    ):
        details = parameter_string.split(
            self.config.trio.delimiter.pack if delimiter is None else delimiter
        )
        if len(details) != len(pack):
            await ctx.edit(
                embed=self.as_embed(
                    f"invalid parameter packs, expected **{len(pack)}**, got **{len(details)}**\n\n"
                    + "\n".join(pack),
                    ctx.author,
                ),
            )
            return None
        return Prodict.from_dict(dict(zip(pack, details)))

    async def check_reserved_cmd(self, ctx: discord.Message, prompt):
        reserved_cmds = ["help", "list", "add", "del", "get", "set", "clear"]
        attempt_cmd = prompt.split(self.config.trio.delimiter.parameter)[0].split(" ")
        if attempt_cmd[0] in reserved_cmds:
            await ctx.edit(
                embed=self.as_embed(
                    f"You probably wanted `!trio{attempt_cmd[0]}`?\nUse `!triohelp` for details\n\nIf you believe this is intentional, try moving this prompt word later in the queue",
                    ctx.author,
                ),
            )
            return False
        return True

    async def check_empty_models(
        self, ctx: discord.Message, model_type: TrioModelType | None = None
    ):
        available = len(self.trio_models)
        if model_type is not None:
            available = len(self.get_models(model_type))
        if available == 0:
            await ctx.edit(
                embed=self.as_embed(
                    "No models are loaded/available\nUse `!trioadd` to load models first",
                    ctx.author,
                ),
            )
            return False
        return True

    async def report_model_index(self, ctx: discord.Message, index, available):
        if index > available:
            await ctx.edit(
                embed=self.as_embed(
                    f"Model index out of range, available **`{available}`**, given **`{index}`**",
                    ctx.author,
                ),
            )
            return False
        return True

    async def report_resource_notfound(
        self, ctx: discord.Message, resource: str, resource_type: str = "ANY"
    ):
        await ctx.edit(
            embed=self.as_embed(
                f"**{resource_type}** resource with name or index {resource} cannot be found",
                ctx.author,
            ),
        )

    async def report_model_outdated(self, ctx: discord.Message, model: TrioModel):
        if model is None:
            return None

        version = self.fetch_model_version(model.urn)
        if version.name == "unknown":
            await ctx.edit(
                embed=self.as_embed(
                    f"**`{TrioModelType(model.model).name}`** model with name {model.name} is outdated or failed to fetch version info",
                    ctx.author,
                ),
            )
            return None
        return version

    async def report_model_empty(self, ctx: discord.Message):
        await ctx.edit(
            embed=self.as_embed(
                "No models are loaded/available\nUse `!trioadd` to load models first",
                ctx.author,
            ),
        )

    @helper.sanitized
    async def get_valid_model(
        self, ctx: discord.Message, model_type: TrioModelType | None, query: str
    ):
        if not await self.check_empty_models(ctx, model_type):
            return None

        model = None
        models = self.get_models(model_type)

        if query.isnumeric():
            index = int(query)
            if not await self.report_model_index(ctx, index, len(models)):
                return None
            model = models[index - 1]
        else:
            model = helper.first(
                models,
                lambda m: helper.iequal(m.name, query) or helper.iequal(m.urn, query),
            )
            if model is None:
                await self.report_resource_notfound(ctx, query)
                return None

        version = await self.report_model_outdated(ctx, model)
        if version is not None:
            return model, version

    async def get_valid_template(self, query: str):
        template = None

        if query.isnumeric() and int(query) <= len(self.user_templates):
            template = self.user_templates[int(query) - 1]
        else:
            template = helper.first(
                self.user_templates, lambda t: helper.iequal(t.name, query)
            )
        return template

    async def add_user_template(
        self, ctx: discord.Message, author: discord.User, detail: str
    ):
        detail = f"name:{detail}"
        details = self.sanitized_parameters(detail)

        if "ckpt" not in details or "prompt" not in details:
            await ctx.edit(
                embed=self.as_embed(
                    f"Follow the syntax to add a template\n"
                    + "```\n!trioadd template <name>|ckpt:<ckpt_index>|[lora:<lora_index>]...|prompt:<base_prompt>|[negative:<text>]|[guidance:0f-30f]|[steps:<0-60>]\n```",
                    author,
                ),
            )

        exist_template = [t for t in self.user_templates if t.name == details.name]
        if len(exist_template) != 0:
            await ctx.edit(
                embed=self.as_embed(
                    f"A template with same name already exist under author {author.name}",
                    author,
                ),
            )
            return

        ckpt = await self.get_valid_model(ctx, TrioModelType.CKPT, details.ckpt)
        if ckpt is None:
            return

        loras = []
        if "lora" in available:
            for addtional_lora in details.lora.split(
                self.config.trio.delimiter.parameter
            ):
                lora_set = addtional_lora.split(self.config.trio.delimiter.modifier)
                weight = 1.0
                if len(lora_set) > 1:
                    weight = float(lora_set[-1])
                lora = await self.get_valid_model(ctx, TrioModelType.LORA, lora_set[0])
                if lora is None:
                    continue
                loras.append((lora, weight))

        prompt = self.config.trio.delimiter.parameter.join(
            [
                p.strip()
                for p in details.prompt.split(self.config.trio.delimiter.parameter)
            ]
        )

        negative_prompt = ""
        if "negative" in available:
            negative_prompt = self.config.trio.delimiter.parameter.join(
                [
                    p.strip()
                    for p in details.negative.split(
                        self.config.trio.delimiter.parameter
                    )
                ]
            )

        guidance = self.config.trio.guidance.default
        if "guidance" in available:
            guidance = max(
                0.0, min(float(details.guidance), self.config.trio.guidance.max)
            )

        steps = self.config.trio.steps.default
        if "steps" in available:
            steps = max(0.0, min(float(details.steps), self.config.trio.steps.max))

        new_template = TrioTemplate(
            details.name,
            author.name,
            ckpt[0].urn,
            {m[0].urn: s for m, s in loras},
            prompt,
            negative_prompt,
            guidance,
            steps,
        )

        self.user_templates.append(new_template)
        self.save_user_templates()

        log_template = Prodict.from_dict(new_template.__dict__)
        log_template.base_model = ckpt[0].name
        log_template.add_models = [f"{m[0].name}, {s}" for m, s in loras]
        log_additional_tab = "\n".join(log_template.add_models)
        log_string = json.dumps(log_template, indent=2)

        await ctx.edit(
            embed=self.as_embed("Added user template", author)
            .add_field(
                name="New Template",
                value=f"```\n{new_template.name}\n```",
                inline=False,
            )
            .add_field(
                name="Base Model",
                value=f"```\n{log_template.base_model}\n```",
                inline=False,
            )
            .add_field(
                name="Addtionals",
                value=f"```\n{log_additional_tab}\n```",
                inline=False,
            )
            .add_field(
                name="Template Prompt",
                value=f"```\n{prompt}\n```",
                inline=False,
            )
            .add_field(
                name="Negative Prompt",
                value=f"```\n{negative_prompt}\n```",
                inline=False,
            )
            .add_field(
                name="Guidance",
                value=f"```\n{guidance}\n```",
                inline=False,
            )
            .add_field(name="Steps", value=f"```\n{steps}\n```", inline=False)
            .set_image(url=ckpt[1].images[0]["url"]),
        )
        self.log(
            ctx,
            f"trio add **Template**, `{new_template.name}`\n```\n{log_string}\n```",
        )

    @helper.sanitized
    async def del_user_template(
        self, ctx: discord.Message, author: discord.User, query: str
    ):
        template = helper.first(self.user_templates, lambda t: t.name, query)
        if template is None:
            return

        self.user_templates.remove(template)
        self.save_user_templates()

        await ctx.edit(
            embed=self.as_embed(
                f"Removed user template, `{template.name}`",
                author,
            ),
        )
        self.log(
            ctx,
            f"trio del **Template**, `{template.name}`",
        )

    @helper.sanitized
    async def create_and_poll_jobs(
        self, ctx: discord.Message, input_model: str, temp: bool = False
    ):
        expected = input_model["quantity"]
        main_job = await civitai.image.create(input=input_model, wait=False)
        token = main_job["token"]

        elapsed = 0
        collected = {}
        completion_time = "failed/unknown status occurred"
        seed = -1
        display_tasks = []
        while (
            len(collected) < expected and elapsed < self.config.trio.concurrent_timeout
        ):
            responses = await civitai.jobs.get(token=token)
            for i, response in enumerate(responses["jobs"]):
                available = response["result"].get("available")
                scheduled = response.get("scheduled")
                if i not in collected and available and not scheduled:
                    display_task = None
                    image_url = response["result"].get("blobUrl")
                    if image_url:
                        image = requests.get(image_url).content

                        seed = self.get_image_seed(image)
                        collected[i] = (image, seed)

                        image_file = discord.File(
                            BytesIO(image),
                            self.get_image_name(len(collected)),
                            description=str(seed),
                        )
                        display_task = ctx.channel.send(file=image_file, silent=True)
                    else:
                        collected[i] = None

                    if display_task is not None:
                        display_tasks.append(asyncio.create_task(display_task))

            await asyncio.sleep(1)
            elapsed += 1

        collected = [c for _, c in collected.items() if c is not None]

        if len(collected) == 0:
            raise Exception("Unable to schedule any job")

        completion_time = helper.timestamp_now()

        artifact = TrioArtifact(
            ctx.author.name,
            completion_time,
            input_model,
            completion_time,
            [s[1] for s in collected if s is not None],
        )

        self.user_artifacts.append(artifact)
        self.save_user_artifacts()
        if not temp:
            self.write_cache(collected, artifact.cache)

        await asyncio.gather(*display_tasks)
        return completion_time

    @helper.sanitized
    async def generate_from_template(
        self,
        ctx: commands.Context | discord.Interaction,
        template_query: str,
        prompts: str,
    ):
        ref = await self.get_ctx_ref(ctx)

        template = await self.get_valid_template(template_query)
        if template is None:
            await self.report_resource_notfound(ref, template_query, "Template")
            return

        input_model = self.create_input_model(template, prompts)
        create_task = asyncio.create_task(self.create_and_poll_jobs(ref, input_model))

        details = [f"```\n{template.name}\n```", f"```\n{prompts}\n```"]

        author = ctx.author if isinstance(ctx, commands.Context) else ctx.user
        embed = self.as_embed(
            self.config.trio.generating_indicator,
            author,
            footer_append="ml-sd-trio",
        )
        embed.add_field(name="Template", value=details[0], inline=False)
        embed.add_field(name="Prompts", value=details[1], inline=False)
        await ref.edit(
            embed=embed,
            view=TrioControlView(self, create_task),
        )

        completion_time = await create_task
        embed.description = self.config.trio.generating_completed
        embed.add_field(name="Ref", value=f"```\n{completion_time}\n```", inline=False)
        await ref.edit(
            embed=embed,
            view=TrioJobView(self),
        )

        self.log(
            ref,
            f"trio ai `{template.name}`\n```{prompts}```",
        )

    @commands.hybrid_command()
    @CogBase.failsafe(CogBase.config.trio.generating_indicator)
    @helper.sanitized
    async def trio(self, ctx: commands.Context, template: str, *, prompts: str):
        """
        Generate images with a trio template resource, random seed
        """

        ref = await self.get_ctx_ref(ctx)

        if not await self.check_reserved_cmd(
            ref, template
        ) or not await self.check_empty_models(ref):
            return

        await self.generate_from_template(ctx, template, prompts)

    @commands.hybrid_command()
    @CogBase.failsafe(force_ephemeral=True)
    async def triohelp(self, ctx: commands.Context):
        """
        Not implemented, no help provided
        """
        pass

    @commands.hybrid_command()
    @CogBase.failsafe(
        CogBase.config.trio.model_querying_indicator, force_ephemeral=True
    )
    async def triolist(self, ctx: commands.Context):
        """
        Query information about all loaded trio resources
        """

        ref = await self.get_ctx_ref(ctx)

        embed = self.as_embed(
            self.config.trio.model_querying_indicator,
            ctx.author,
            footer_append="ml-sd-trio",
        )
        message = await ref.edit(
            embed=embed,
        )
        embed.description = ""

        versioned_trio_models = [
            {"model": model, "version": self.fetch_model_version(model.urn).name}
            for model in self.trio_models
        ]

        model_types = [
            (TrioModelType.CKPT, "**Checkpoints**(`CKPT`)"),
            (TrioModelType.LORA, "**LORA models**(`LORA`)"),
            (TrioModelType.VAE, "**Var autoencoders**(`VAE`)"),
        ]
        # models
        for model_type, header in model_types:
            models = [
                m for m in versioned_trio_models if m["model"].model == model_type
            ]
            if len(models) > 0:
                embed.add_field(
                    name=f"{header}: {len(models)} added",
                    value="\n".join(
                        [
                            f"{i + 1}. **{model['model'].name}**, {model['version']}"
                            for i, model in enumerate(models)
                        ]
                    ),
                    inline=False,
                )
        # templates
        if len(self.user_templates) > 0:
            embed.add_field(
                name=f"Templates: {len(self.user_templates)} added",
                value="\n".join(
                    [
                        f"{i + 1}. **{template.name}**"
                        for i, template in enumerate(self.user_templates)
                    ]
                ),
                inline=False,
            )
        # cache
        if len(self.user_artifacts) > 0:
            self.invalidate_cache()
            embed.add_field(
                name=f"Cache: {len(self.user_artifacts)} available",
                value=f"Oldest is `{self.user_artifacts[-1].timestamp}`",
                inline=False,
            ),

        await message.edit(embed=embed)

    @commands.hybrid_command()
    @CogBase.failsafe(
        CogBase.config.trio.model_querying_indicator, force_ephemeral=True
    )
    @helper.sanitized
    async def trioadd(self, ctx: commands.Context, trio_type: str, *, detail: str):
        """
        Add a trio resource
        """

        ref = await self.get_ctx_ref(ctx)

        if trio_type.lower() == "template":
            await self.add_user_template(ref, ctx.author, detail)
            return
        else:
            trio_type = await self.validate_model_type(ref, trio_type)
            if trio_type is None:
                return

        details = await self.expect_parameters(ref, ["name", "urn"], detail)
        if details is None:
            return
        if details.name.isnumeric():
            await ref.edit(
                embed=self.as_embed(
                    "Model name cannot be numeric only",
                    ctx.author,
                ),
            )
            return

        new_model = TrioModel(trio_type, **details)
        model_type = TrioModelType(new_model.model).name.upper()
        exist_model = helper.first(
            self.trio_models, lambda m: helper.iequal(m.urn, new_model.urn)
        )
        if exist_model is not None:
            await ref.edit(
                embed=self.as_embed(
                    f"A **`{model_type}`** "
                    + f"model with same resource urn already exists\n```\n{exist_model.name}\n```",
                    ctx.author,
                ),
            )
            return
        version = await self.report_model_outdated(ref, new_model)
        if version is None:
            return

        self.trio_models.append(new_model)
        self.save_trio_models()
        thumbnail = version["images"][0]["url"]
        await ref.edit(
            embed=self.as_embed(
                f"Added new **`{model_type}`**, {new_model.name} @ `{version.name}`",
                ctx.author,
            ).set_image(url=thumbnail),
        )
        self.log(
            ctx.message,
            f"trio add **{model_type}**\n```\n{new_model.name} @ {version.name}\n```",
        )

    @commands.hybrid_command()
    @CogBase.failsafe(
        CogBase.config.trio.model_querying_indicator, force_ephemeral=True
    )
    @helper.sanitized
    async def triodel(self, ctx: commands.Context, trio_type: str, query: str):
        """
        Delete a trio resource by its index or name
        """

        ref = await self.get_ctx_ref(ctx)

        if trio_type.lower() == "template":
            await self.del_user_template(ref, ctx.author, query)
            return
        else:
            trio_type = await self.validate_model_type(ref, trio_type)
            if trio_type is None:
                return

        model = await self.get_valid_model(ref, trio_type, query)
        if model is None:
            return
        model = model[0]

        model_type = TrioModelType(model.model).name.upper()
        deleter = helper.first(
            self.trio_models, lambda m: helper.iequal(m.urn, model.urn)
        )
        if deleter is not None:
            self.trio_models.remove(deleter)
        self.save_trio_models()
        await ref.edit(
            embed=self.as_embed(
                f"Removed `{model_type}`, **{model.name}**",
                ctx.author,
            ),
        )
        self.log(
            ctx.message,
            f"trio del **{model_type}**\n```\n{model.name}\n```",
        )

    @commands.hybrid_command()
    @CogBase.failsafe(
        CogBase.config.trio.model_querying_indicator, force_ephemeral=True
    )
    @helper.sanitized
    async def trioget(self, ctx: commands.Context, trio_type: str, *, query: str):
        """
        Query information about a specific trio resource by its index or name
        """
        ref = await self.get_ctx_ref(ctx)

        if trio_type.lower() == "template":
            template = await self.get_valid_template(query)
            if template is None:
                await self.report_resource_notfound(ref, query, "Template")
                return

            ckpt = await self.get_valid_model(
                ref, TrioModelType.CKPT, template.base_model
            )
            log_template = Prodict.from_dict(template.__dict__)
            log_template.base_model = ckpt[0].name
            log_template.add_models = {}
            for urn, s in template.add_models.items():
                lora = await self.get_valid_model(ref, TrioModelType.LORA, urn)
                log_template.add_models[lora[0].name] = s
            log_additional_tab = "\n".join(
                [f"- {m}, {s}" for m, s in log_template.add_models.items()]
            )

            short_cut = f"{template.name}|ckpt:{ckpt[0].name}"
            if len(log_template.add_models) > 0:
                short_cut_string = self.config.trio.delimiter.parameter.join(
                    [
                        f"{m}{self.config.trio.delimiter.modifier}{s}"
                        for m, s in log_template.add_models.items()
                    ]
                )
                short_cut += f"|lora:{short_cut_string}"
            short_cut += (
                f"|prompt:{template.base_prompt}|negative:{template.negative_prompt}"
            )
            short_cut += f"|guidance:{template.guidance}|steps:{template.steps}"

            await ref.edit(
                embed=self.as_embed("", ctx.author)
                .add_field(
                    name="Template",
                    value=f"```\n{template.name}\n```",
                    inline=False,
                )
                .add_field(
                    name="Base Model",
                    value=f"```\n{log_template.base_model}\n```",
                    inline=False,
                )
                .add_field(
                    name="Addtionals",
                    value=f"```\n{log_additional_tab}\n```",
                    inline=False,
                )
                .add_field(
                    name="Template Prompt",
                    value=f"```\n{log_template.base_prompt}\n```",
                    inline=False,
                )
                .add_field(
                    name="Negative Prompt",
                    value=f"```\n{log_template.negative_prompt}\n```",
                    inline=False,
                )
                .add_field(
                    name="Guidance",
                    value=f"```\n{log_template.guidance}\n```",
                    inline=False,
                )
                .add_field(
                    name="Steps", value=f"```\n{log_template.steps}\n```", inline=False
                )
                .add_field(
                    name="Shortcut", value=f"```\n{short_cut}\n```", inline=False
                )
                .set_image(url=ckpt[1].images[0]["url"]),
            )
            return
        elif trio_type.lower() == "cache":
            artifact = helper.first(self.user_artifacts, lambda a: a.cache == query)
            if artifact is not None:
                cache = self.fetch_cache(artifact)
                if cache is not None:
                    await ref.edit(file=discord.File(cache, f"artifact_{query}.zip"))
                    return
            await self.report_resource_notfound(ref, query, "CACHE")
        else:
            model_type = await self.validate_model_type(ref, trio_type)
            model = await self.get_valid_model(ref, model_type, query)
            if model is not None:
                await ref.edit(
                    embed=self.as_embed("", ctx.author)
                    .add_field(
                        name=model[0].name,
                        value=f"```\n{TrioModelType(model_type).name}\n```",
                        inline=False,
                    )
                    .add_field(
                        name="Version",
                        value=f"```\n{model[1].name}\n```",
                        inline=False,
                    )
                    .add_field(
                        name="Uri", value=f"```\n{model[0].urn}\n```", inline=False
                    )
                    .set_image(url=model[1].images[0]["url"]),
                )
                return
            await self.report_resource_notfound(ref, query)
