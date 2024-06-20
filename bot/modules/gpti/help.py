import discord


async def generate_help_info(ref: discord.Message):
    color = discord.Color.from_rgb(236, 248, 248)
    help_info = [
        discord.Embed(
            color=color,
            title="GPT图片生成",
            description="""
        使用DALL·E进行图片生成, powered by OpenAI.

        已提供`dall-e-2`和`dall-e-3`模型.
        
        每月配额: 1,000.

        """,
        ),
        discord.Embed(
            color=color,
            title="命令指南及其示例:",
            description=f"""
        **触发方式: `!gpti` 聊天命令 或  `/gpti` discord命令.**

        ```
gpti : 给定文字prompt生成图片```

        例如, 生成1张小猫抱着鱼狂奔的图片
        ```
gpti 小猫在集市中抱着一条鱼鱼狂奔, 背后人们穷追不舍!```
        """,
        ),
        discord.Embed(
            color=color,
            title="风格",
            description=f"""
        使用`dall-e-3`模型时, 允许设定风格参数.

- 生动: 生成超真实和戏剧性的图像.
- 自然: 生成符合规律, 较少超真实感的图像.
            """,
        ),
        discord.Embed(
            color=color,
            title="关于每月配额(?)",
            description=f"""
        DroppyBot每月为每人分配了`1,000`配额的gpti使用量, 当您生成图片时, 会根据使用的参数消耗配额.

- 生成一张`dall-e-2`图片消耗`0.5`配额.
- 生成一张`dall-e-3`图片消耗`1.0`配额.
 - 生成`HD (高细节)`图片时, 额外消耗`1.0`配额.
 - 生成**大于**`1024x1024`尺寸的图片时, 额外消耗`1.0`配额.

        概括: 每人每月大概能使用`dall-e-3`生成500张标准大小的高细节图
            """,
        ),
        discord.Embed(
            color=color,
            title="系列生成(多张): (已停用)",
            description=f"""
gpti : 给定文字prompt生成多张类似风格的图片变种

        例如, 生成5张珠穆朗玛峰填平东非大裂谷的图片
        ```
gpti x5 珠穆朗玛峰填平东非大裂谷```
        """,
        ),
    ]

    await ref.edit(embeds=help_info)
