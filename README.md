# Droppy Bot 自用DC机器人

![version](https://img.shields.io/badge/DroppyBot-1.0.0-R.svg)


> 于开黑嬉闹中写就, 待夜深人静时完工. 在远程服务器运行, 供好友娱乐间使用😅


## Brief

+ gpt
    + 使用`chatGPT`进行文字补全
    + 可附加有上限的上下文(128k context)
    + 可回复机器人消息以模拟对话(包含此对话上下文)
    + 可使用`gpt-4-turbo`或`gpt-4o`模型
+ gpti
    + 使用`DALL-E3`进行图片生成
    + 提供`256`, `512`, 以及`1024`像素
+ tts(*已移除*, 需要机器人代言的人已不在😢)
    + 使用`azure-cognitive-service`进行文字转语音
    + 转播用户的文字消息
    + 分辨消息类型(图片, 链接, mention, 表情/符号, 回复)
+ trio
    + 使用`Stable Diffusion`进行图片生成
    + 动态加载不同模型(CKPT, LORA, VAE), 目前支持civitai导入
    + 下载缓存
    + 重练

所有模块均可使用`!`文字前缀触发或discord命令`/`


## Consume

+ [Python 3.8+](https://www.python.org/downloads/)

```
git clone https://github.com/gottyduke/DroppyBot
cd DroppyBot
pip install -r requirements.txt
```


## Required Environments 

| env                 | detail            |
| ------------------- | ----------------- |
| `BOT_TOKEN`         | discord bot token |
| `DEV_CHANNEL`       | log channel id    |
| `DEV_ID`            | dev user id       |
| `OPENAI_KEY`        | openAI API token  |
| `CIVITAI_API_TOKEN` | civitai API token |


## Module Documentation

All modules can be invoked using the `!` text prefix or with the Discord command `/`.
All modules configurations can be tweaked in `bot/rules/config.json` file.
Features are added/changed/removed/broken as I update the bot for my personal use.

> `!cmd ....` or `/cmd`


### gpt

| cmd    | arg      | detail                                 |
| ------ | -------- | -------------------------------------- |
| `gpt`  | `prompt` | provide prompt for `gpt-4-turbo` model |
| `gpt4` | `prompt` | provide prompt for `gpt-4o` model      |

To continue a contextual conversation, by replying to bot's response message, aka chat memory.


### gpti

| cmd    | arg           | detail                                                            |
| ------ | ------------- | ----------------------------------------------------------------- |
| `gpti` | `prompt`      | provide prompt for `DALL-E`, in natural language                  |
| `gpti` | `xN` `prompt` | provide prompt for `DALL-E`, in natural language, batch N at once |


Uses `DALL-E3` for image generation.
Image resolutions of `256`, `512`, and `1024` pixels.


### trio

| cmd        | arg                               | detail                                                               |
| ---------- | --------------------------------- | -------------------------------------------------------------------- |
| `trio`     | `template name or index` `prompt` | invoke image generation job using a loaded trio template, batch of 8 |
| `triolist` | ``                                | list all loaded trio resources                                       |
| `trioget`  | `type` `name or index`            | query information about a trio resource                              |
| `trioadd`  | `type` `details`                  | add a trio resource                                                  |
| `triodel`  | `type` `name or index`            | remove a trio resource                                               |


### `trio` resource

| type       | description     |
| ---------- | --------------- |
| `ckpt`     | Checkpoint      |
| `lora`     | Lora            |
| `vae`      | Var autoencoder |
| `template` | Trio template   |

### add `trio` resource from external source (only supports civitai for now)

`trioadd ckpt <Checkpoint name>|urn:air:xxxxxx:xxxxxx:civitai:xxxxxx@xxxxxx`   
`trioadd lora <Lora model name>|urn:air:xxxxxx:xxxxxx:civitai:xxxxxx@xxxxxx`   
`trioadd vae <Vae name>|urn:air:xxxxxx:xxxxxx:civitai:xxxxxx@xxxxxx`   

Resource name here are just internal identifiers, not required to be the same as the actual model

e.g. `trioadd ckpt Pony Diffusion XL | urn:air:pony:checkpoint:civitai:257749@290640`

### add `trio` template

`trioadd template <TemplateName>|<details>`

`TemplateName` must contain no space.  
The details are constructed with parameter value pair, `paramter:value`, and separated by `|`   


| parameter  | value                         | description                                                                    |
| ---------- | ----------------------------- | ------------------------------------------------------------------------------ |
| `ckpt`     | `name or index`               | a loaded `ckpt` trio resource                                                  |
| `lora`     | `name or index` `[^strength]` | optional, accepts multiple, each lora separated by `,`, default strength `1.0` |
| `prompt`   | `word,word,word`              | base template prompt, appended to each generation                              |
| `negative` | `word,word,word`              | optional, base negative prompt, appended to each generation                    |
| `steps`    | `number`                      | optional, up to `60`, default `60`                                             |
| `guidance` | `number`                      | optional, up to `30.0`, default `8.0`                                          |


Given loaded trio resource from `triolist`:
```
Checkpoints(CKPT): 3 added
1. Pony Diffusion V6 XL, V6 (start with this one)
2. AutismMix SDXL, AutismMix_pony
3. reweik_PonyXL, v01.2

LORA models(LORA): 12 added
1. Detail Tweaker XL, v1.0
2. Styles for Pony Diffusion V6 XL , Faux Oil Painting Soft
3. Fritia Symphony of Frenzy, v01
```

e.g. 
```
trioadd template my_basic_template
|ckpt:2
|lora:1^1.5,2,3^0.7
|prompt:score_9,score_8_up,score_7_up,score_6_up,score_5_up,score_4_up,best quality,masterpiece,4k,prefect lighting,rating explicit,anime,1girl,(solo:1.2),uncensored,sb-fritia-sof,shoulders,pink hair,frills,choker,thighhighs,shoes,hair ornament,thigh strap,leotard,arm garter,bracelet,wide hips,(steaming body:1.2),sweat,blush,heavy breathing,sound effects,blush,(looking at viewer:1.2),detailed
|negative:bad_hands,source_pony,source_furry,3d,frame,logo,signature,censored,disembodied_limb,spy x family,brown hair,bad_feet,bad_toes,blue hair,yellow hair
```
This will add a template using checkpoint `AutismMix SDXL`, with additional loras of `Detail Tweaker XL` at strength `1.5`, `Styles for Pony Diffusion V6 XL` at strength `1.0`, `Fritia Symphony of Frenzy` at strength `0.7`, default guidance of `8.0`, and default steps at `60`

You can review the template by `trioget template my_basic_template`

> If using discord command style `/`, it's suggested to not use linebreaks to format your parameter packs

---
<p align="center">Dropkicker @ 2024</p>
