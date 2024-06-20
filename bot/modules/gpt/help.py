import discord


async def generate_help_info(ref: discord.Message):
    help_info = [
        discord.Embed(
            color=discord.Color.blurple(),
            title="GPT",
            description="""
        使用chatGPT进行文字生成, powered by OpenAI.

        可附加有上限的上下文, 模拟连续对话(参考使用方法).

        已提供`gpt-4-turbo`或`gpt-4o`**(新!)**模型.
        """,
        )
        .add_field(
            name="*2024/05/16 更新:*",
            value="""
        + 移除了`gpt-3.5-turbo`, 现有的`!gpt`命令将会指向`gpt-4-turbo`
        + 添加了`gpt-4o`模型, 现有的`!gpt4`命令将会指向它
        """,
            inline=False,
        )
        .add_field(
            name="2024/04/06 更新:",
            value="""
        + 训练数据已更新至2023年12月份
        """,
            inline=False,
        )
        .add_field(
            name="2024/03/24 更新:",
            value="""
        + gpt模型`1106`->`0125`
        """,
            inline=False,
        )
        .add_field(
            name="2023/12/18 更新:",
            value="""
        + 初步支持联网搜索, 结果基于互联网查找
        """,
            inline=False,
        )
        .add_field(
            name="2023/11/19 更新:",
            value="""
        + 训练数据已更新至2023年4月份
        + 支持长文本输入/输出(参考使用方法)
        + 支持图片识别/图片辅助的文字生成(参考使用方法)
        """,
            inline=False,
        ),
        discord.Embed(
            color=discord.Color.blurple(),
            title="如何选择不同的模型?",
            description=f"""
        本机器人🔧接入了OpenAI API, 自2023/3/27也获得了gpt-4模型API的内测资格, ~~因此提供gpt-3.5-turbo和gpt-4两种模型~~

        ~~其中`gpt-3.5-turbo`是OpenAI默认chatGPT模型, 而`gpt-4`则是其之后的高级付费模型, 语言能力和逻辑思维得到了很大的加强~~

        ~~两GPT模型的使用**没有**网页端的每小时条数限制. 但是, 作为一个计费制的API, 在整活类问题/逻辑需求不强的使用场景下请调用`gpt-3.5-turbo`模型, 正常使用时则调用`gpt-4`模型~~

        现已移除`gpt-3.5-turbo`, 默认设置为`gpt-4-turbo`, 高级模型为`gpt-4o`.

        """,
        ),
        discord.Embed(
            color=discord.Color.blurple(),
            title="命令指南及其示例:",
            description=f"""
        **触发方式: `!gpt` 聊天命令 或  `/gpt` discord命令.**

        ```
gpt : 开始一个新的对话, 指定使用gpt-4-turbo模型
gpt4 : 开始一个新的对话, 指定使用gpt-4o模型
gptinit : 设定个人专属的GPT设定语句, 例如人格模拟/风格设定```

        取自于群友日常使用场景😅(文字命令):

        询问`gpt`对于攀登高山的看法:
        ```
!gpt 你对於爬高山有什么看法?```
        使用`gpt-4`用诗的形式证明素数的无穷性:
        ```
!gpt4 用诗的形式证明素数的无穷性```
        辅助生产力:
        ```
!gpt4 如何写一个好的开题报告? 我的方向是XXXX, 需要注重XXXX, XXXX```
        进行双语对照翻译:
        ```
!gpt4 "命里有时终须有，命里无时莫强求"这句话用俄语如何翻译? 要求尽量信达雅, 并逐句附加中俄双语对照和解释```
        """,
        ),
        discord.Embed(
            color=discord.Color.blurple(),
            title="附加上下文进行连续对话",
            description=f"""
        每次使用GPT命令时, 便开启了一个**新的对话**.

        若要跟随此对话上下文进行连续对话, 请右键该🤖消息, 选择回复即可.

        当使用回复跟随上下文继续对话时, **不需要再次使用**GPT命令, 请直接输入你的文字.

        你可以随时从任意对话节点中开启上下文.
        """,
        ).set_image(
            url="https://cdn.discordapp.com/attachments/1084950188617117817/1252747524930928704/reply.png?ex=6673578c&is=6672060c&hm=9f42829d85c20d30a1f5ee24787671420e1095eb2b50ab5b7cd3b85c2d72d0dd&"
        ),
        discord.Embed(
            color=discord.Color.blurple(),
            title="关于GPT设定语句",
            description=f"""
        GPT设定语句是每次对话时各用户专属的前置设定, 又称为调教, 咒语, system prompt等.

        例如, 使GPT扮演一个猫娘:
        ```
gptinit 你将扮演一个猫娘, 称呼我为主人, 开头和结尾都要使用喵语气和可爱风格```

        若要清空GPT设定语句, 则使用不加参数的`gptinit`命令.
        """,
        ),
        discord.Embed(
            color=discord.Color.blurple(),
            title="附加文件用于文字生成",
            description=f"""
        使用GPT命令时, 将文件拖拽至输入栏即可附加此文件用于下次文字生成.

        机器人不支持如`.docx`, `.pdf`等格式的自动转换, 文档类文件请自行转换为纯文本格式(`.txt`), 代码类文件可直接附加.

        可一次附加多个文件.

        此功能仅限文字命令`!`触发.
        """,
        ).set_image(
            url="https://cdn.discordapp.com/attachments/1084950188617117817/1252751979415863396/1.png?ex=66735bb2&is=66720a32&hm=48264bcf2a58f6bc7f2ecf61637974a5b950c17fea7bd9f43354a961f9195c44&"
        ),
        discord.Embed(
            color=discord.Color.blurple(),
            title="附加图片进行图片识别/辅助生成",
            description=f"""
        使用GPT命令时, 将图片拖拽/复制至输入栏即可附加此图片用于下次图片识别/辅助生成.

        机器人不支持图形交换格式(`.gif`, 即动图), 请使用常见图片格式(`.jpg`, `.png`).

        可一次附加多个图片.

        此功能仅限文字命令`!`触发.
        """,
        ).set_image(
            url="https://cdn.discordapp.com/attachments/1084950188617117817/1252752112715042907/2.png?ex=66735bd2&is=66720a52&hm=b1767b48282606588a7550af930cf5b1462f4aa224f209084e96fa85e313719c&"
        ),
    ]

    await ref.edit(embeds=help_info)
