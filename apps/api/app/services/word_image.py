from __future__ import annotations

"""根据英文单词 / 中文释义解析配图主题键，保证示意与词义对齐。"""

import re
from typing import Tuple

# (主题键, 中文标签, 匹配模式) — 越靠前优先级越高
_THEME_RULES: list[Tuple[str, str, str]] = [
    ("school", "学校", r"学校|教师|老师|学生|同学|教室|课堂|课本|作业|考试|测验|课程|学科|教育|年级|分数|图书馆|操场|校园|毕业|班长|笔记|知识|学习|教"),
    ("book", "书本", r"书|本|词典|阅读|读|写|钢笔|铅笔|尺子|橡皮|黑板|笔记本"),
    ("family", "家庭", r"家庭|父亲|母亲|父母|兄弟|姐妹|儿子|女儿|祖父|祖母|叔叔|阿姨|亲戚|邻居|丈夫|妻子|结婚|夫妇|家"),
    ("food", "饮食", r"吃|饭|餐|食|菜|肉|鱼|蛋|奶|面包|水果|苹果|喝|水|茶|咖啡|饿|渴|味道|早餐|午餐|晚餐|厨房"),
    ("transport", "出行", r"车|火车|汽车|公交|飞机|船|骑|驾驶|路|街|桥|站|交通|旅行|票|地图"),
    ("shop", "购物", r"买|卖|钱|商店|价格|便宜|贵|购物|市场|衣服|鞋|袋"),
    ("health", "健康", r"医|病|药|健康|痛|医院|感冒|发烧|护士|病人|伤|治疗"),
    ("nature", "自然", r"山|河|海|湖|树|花|草|自然|环境|雨|雪|太阳|月亮|风|云|天|地|污染|保护"),
    ("sport", "运动", r"球|足球|篮球|跑|跳|游|运动|玩|踢|比赛|赢|输|爱好|音乐"),
    ("emotion", "情感", r"开心|快乐|高兴|难过|伤心|爱|喜欢|怕|害怕|怒|生气|情|感|兴|兴趣|希望|愿望"),
    ("tech", "科技", r"电|电脑|网络|手机|电话|科技|信息|机器|屏幕|键盘|互联网"),
    ("time", "时间", r"时|日|年|周|月|早|晚|昨天|今天|明天|分钟|小时|秒|季节|春|夏|秋|冬|周末"),
    ("person", "人物", r"人|男人|女人|男孩|女孩|朋友|高|矮|胖|瘦|美|年轻|老|性格|描述"),
    ("social", "交往", r"说|讲|听|问|答|帮|请|谢|打招呼|介绍|邀请|交流|社会|礼貌"),
    ("animal", "动植物", r"猫|狗|鸟|鱼|马|牛|羊|猪|鸡|动物|植物|叶子|种子|熊|虎|虫"),
    ("body", "身体", r"手|头|眼|睛|脚|腿|身|口|耳|鼻|脸|牙|头发|心脏|胃|臂"),
    ("color", "颜色", r"红|蓝|绿|黄|白|黑|色|圆|方|形|三角|长|短"),
    ("item", "用品", r"桌|椅|床|门|窗|杯|袋|箱|灯|钟|镜|牙刷|肥皂|伞|钥匙"),
    ("holiday", "节日", r"节|假|庆|生日|派对|礼物|旅行|假期|圣诞|春节"),
    ("culture", "文化", r"国|语|文|化|城|首都|旗|世界|外国|中国|美国|英国"),
    ("action", "动作", r"走|跑|跳|看|做|拿|给|来|去|开|关|找|用|开始|结束|帮助|工作"),
    ("house", "住所", r"房子|房间|卧室|客厅|厨房|浴室|楼|公寓"),
]

# 英文单词直接主题
_WORD_THEME = {
    "school": "school",
    "teacher": "school",
    "student": "school",
    "book": "book",
    "read": "book",
    "write": "book",
    "family": "family",
    "father": "family",
    "mother": "family",
    "home": "house",
    "house": "house",
    "room": "house",
    "car": "transport",
    "bus": "transport",
    "train": "transport",
    "plane": "transport",
    "ship": "transport",
    "bike": "transport",
    "buy": "shop",
    "sell": "shop",
    "money": "shop",
    "hospital": "health",
    "doctor": "health",
    "ill": "health",
    "tree": "nature",
    "flower": "nature",
    "rain": "nature",
    "sun": "nature",
    "football": "sport",
    "run": "sport",
    "swim": "sport",
    "happy": "emotion",
    "sad": "emotion",
    "love": "emotion",
    "computer": "tech",
    "phone": "tech",
    "telephone": "telephone",
    "time": "time",
    "day": "time",
    "year": "time",
    "friend": "person",
    "boy": "person",
    "girl": "person",
    "cat": "animal",
    "dog": "animal",
    "bird": "animal",
    "hand": "body",
    "head": "body",
    "eye": "body",
    "red": "color",
    "blue": "color",
    "green": "color",
    "table": "item",
    "chair": "item",
    "door": "item",
    "holiday": "holiday",
    "party": "holiday",
    "china": "culture",
    "country": "culture",
    "go": "action",
    "come": "action",
    "see": "action",
    "make": "action",
    "unhappy": "unhappy",
    "angle": "angle",
    "projection": "projection",
    "geometry": "geometry",
    "vertical": "vertical",
    "intersect": "intersect",
    "demonstrate": "demonstrate",
    "accurate": "accurate",
    "telephone": "telephone",
}


def theme_label(theme: str) -> str:
    for key, label, _ in _THEME_RULES:
        if key == theme:
            return label
    labels = {
        "unhappy": "不开心",
        "telephone": "电话",
        "angle": "角",
        "plane": "平面",
        "projection": "投影",
        "geometry": "几何",
        "vertical": "垂直",
        "intersect": "相交",
        "demonstrate": "演示",
        "accurate": "准确",
        "shape": "词义",
    }
    return labels.get(theme, "词义")


def resolve_theme(word: str = "", meaning: str = "", image_key: str = "") -> str:
    """返回配图主题键。"""
    key = (image_key or word or "").lower().strip()
    if key in _WORD_THEME:
        return _WORD_THEME[key]
    # 精选主题键直接透传
    curated = {
        "unhappy",
        "telephone",
        "angle",
        "plane",
        "projection",
        "geometry",
        "vertical",
        "intersect",
        "demonstrate",
        "accurate",
    }
    if key in curated:
        return key

    text = f"{word} {meaning}".lower()
    # 中文优先
    for theme, _label, pattern in _THEME_RULES:
        if re.search(pattern, meaning or ""):
            return theme
    # 英文粗匹配
    for theme, _label, pattern in _THEME_RULES:
        # 用主题英文词粗匹配 word
        if theme in (word or "").lower():
            return theme
    if key:
        return key
    return "shape"


def theme_icon(theme: str) -> str:
    mapping = {
        "school": "school",
        "book": "book",
        "family": "family",
        "food": "food",
        "transport": "car",
        "shop": "shop",
        "health": "health",
        "nature": "nature",
        "sport": "sport",
        "emotion": "smile",
        "tech": "tech",
        "time": "time",
        "person": "person",
        "social": "speak",
        "animal": "animal",
        "body": "body",
        "color": "color",
        "item": "item",
        "holiday": "holiday",
        "culture": "globe",
        "action": "run",
        "house": "house",
        "unhappy": "cross",
        "telephone": "phone",
        "angle": "angle",
        "plane": "plane",
        "projection": "throw",
        "geometry": "shape",
        "vertical": "vertical",
        "intersect": "cross",
        "demonstrate": "board",
        "accurate": "target",
    }
    return mapping.get(theme, "shape")
