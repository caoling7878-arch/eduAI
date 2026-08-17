from __future__ import annotations

"""把词库条目拆成「一词多性 / 一词多义」，并为每个义项配中考风格例句。"""

import re
from typing import Any, Dict, List

from .vocab_exam_examples import lookup_exam_examples

# 中考阅读 / 完形常见句式：每个义项一条，尽量覆盖不同词性。
# key = 小写单词；value = [{pos, text, example, example_cn}]
SENSE_BANK: Dict[str, List[Dict[str, str]]] = {
    "school": [
        {"pos": "n.", "text": "学校", "example": "There is a new school near my home.", "example_cn": "我家附近有一所新学校。"},
    ],
    "learn": [
        {"pos": "v.", "text": "学习，学会", "example": "We can learn a lot from this reading passage.", "example_cn": "我们可以从这篇阅读短文学到很多。"},
    ],
    "teacher": [
        {"pos": "n.", "text": "教师", "example": "Our teacher asked us to read the text aloud.", "example_cn": "老师让我们大声朗读课文。"},
    ],
    "student": [
        {"pos": "n.", "text": "学生", "example": "Every student should finish the paper on time.", "example_cn": "每个学生都应该按时完成试卷。"},
    ],
    "study": [
        {"pos": "v.", "text": "学习，研究", "example": "If you study hard, you will get good grades.", "example_cn": "如果你努力学习，就会取得好成绩。"},
        {"pos": "n.", "text": "学习；研究", "example": "A new study shows that reading every day helps students a lot.", "example_cn": "一项新研究表明，每天阅读对学生很有帮助。"},
    ],
    "test": [
        {"pos": "n.", "text": "测试，测验", "example": "We will have an English test next Monday.", "example_cn": "下周一我们将有一场英语测验。"},
        {"pos": "v.", "text": "测试，检验", "example": "The teacher will test us on the new words.", "example_cn": "老师将测验我们这些新单词。"},
    ],
    "mark": [
        {"pos": "n.", "text": "分数；记号", "example": "She got a high mark in the math exam.", "example_cn": "她在数学考试中得了高分。"},
        {"pos": "v.", "text": "做标记；批改", "example": "Please mark the important sentences in the passage.", "example_cn": "请在短文中标出重要句子。"},
    ],
    "review": [
        {"pos": "v.", "text": "复习；回顾", "example": "We should review our notes before the exam.", "example_cn": "考试前我们应该复习笔记。"},
        {"pos": "n.", "text": "复习；评论", "example": "A quick review of the lesson helped him remember the key points.", "example_cn": "快速复习这一课帮助他记住了要点。"},
    ],
    "progress": [
        {"pos": "n.", "text": "进步；进展", "example": "She has made great progress in English this term.", "example_cn": "这学期她的英语有了很大进步。"},
        {"pos": "v.", "text": "进展，前进", "example": "The project is progressing well.", "example_cn": "这个项目进展顺利。"},
    ],
    "discipline": [
        {"pos": "n.", "text": "纪律", "example": "Good discipline is important in every classroom.", "example_cn": "每个教室里良好的纪律都很重要。"},
        {"pos": "v.", "text": "管教", "example": "Parents should discipline their children with love.", "example_cn": "父母应该用爱来管教孩子。"},
    ],
    "graduate": [
        {"pos": "v.", "text": "毕业", "example": "He will graduate from junior high school this June.", "example_cn": "他将于今年六月初中毕业。"},
        {"pos": "n.", "text": "毕业生", "example": "The graduates took photos in front of the school gate.", "example_cn": "毕业生们在校门口拍照。"},
    ],
    "break": [
        {"pos": "n.", "text": "课间休息；间歇", "example": "We often play basketball during the break.", "example_cn": "课间休息时我们常打篮球。"},
        {"pos": "v.", "text": "打破；弄坏", "example": "Be careful not to break the glass.", "example_cn": "小心别把玻璃杯打破。"},
    ],
    "report": [
        {"pos": "n.", "text": "报告", "example": "Students must write a report after the science class.", "example_cn": "科学课结束后学生必须写一份报告。"},
        {"pos": "v.", "text": "报告，汇报", "example": "Please report the problem to your teacher at once.", "example_cn": "请立刻把这个问题报告给老师。"},
    ],
    "note": [
        {"pos": "n.", "text": "笔记；便条", "example": "I wrote a note to remember the new words.", "example_cn": "我写了一张便条来记住这些新词。"},
        {"pos": "v.", "text": "注意；记下", "example": "Please note that the exam starts at 8:00.", "example_cn": "请注意考试八点开始。"},
    ],
    "answer": [
        {"pos": "n.", "text": "答案", "example": "Write your answer on the answer sheet.", "example_cn": "把答案写在答题卡上。"},
        {"pos": "v.", "text": "回答", "example": "Can you answer this question in English?", "example_cn": "你能用英语回答这个问题吗？"},
    ],
    "home": [
        {"pos": "n.", "text": "家", "example": "There is no place like home.", "example_cn": "没有一个地方比得上家。"},
        {"pos": "adv.", "text": "在家；回家", "example": "I usually go home after school.", "example_cn": "我通常放学后回家。"},
    ],
    "support": [
        {"pos": "v.", "text": "支持", "example": "My parents always support me when I try new things.", "example_cn": "我尝试新事物时父母总是支持我。"},
        {"pos": "n.", "text": "支持；支撑", "example": "We need more support from our teachers.", "example_cn": "我们需要老师更多的支持。"},
    ],
    "love": [
        {"pos": "v.", "text": "爱；喜爱", "example": "I love reading books in the library.", "example_cn": "我喜欢在图书馆读书。"},
        {"pos": "n.", "text": "爱", "example": "A mother's love is the greatest of all.", "example_cn": "母爱是最伟大的。"},
    ],
    "drink": [
        {"pos": "v.", "text": "喝", "example": "We should drink enough water every day.", "example_cn": "我们每天应该喝足够的水。"},
        {"pos": "n.", "text": "饮料", "example": "Would you like a cold drink after the match?", "example_cn": "比赛后你想喝杯冷饮吗？"},
    ],
    "ride": [
        {"pos": "v.", "text": "骑，乘", "example": "He learned to ride a bike when he was six.", "example_cn": "他六岁时学会了骑自行车。"},
        {"pos": "n.", "text": "乘坐；骑行", "example": "It is a short bus ride from school to the museum.", "example_cn": "从学校坐公交去博物馆很近。"},
    ],
    "walk": [
        {"pos": "v.", "text": "步行", "example": "I walk to school every morning.", "example_cn": "我每天早上步行去学校。"},
        {"pos": "n.", "text": "散步；步行", "example": "Let's take a walk in the park after dinner.", "example_cn": "晚饭后我们去公园散步吧。"},
    ],
    "travel": [
        {"pos": "v.", "text": "旅行", "example": "Many families travel during the summer holiday.", "example_cn": "许多家庭在暑假旅行。"},
        {"pos": "n.", "text": "旅行", "example": "Travel by train is cheap and comfortable.", "example_cn": "坐火车旅行既便宜又舒适。"},
    ],
    "turn": [
        {"pos": "v.", "text": "转动；转弯", "example": "Turn left at the second crossing.", "example_cn": "在第二个十字路口向左转。"},
        {"pos": "n.", "text": "转弯；轮次", "example": "It's your turn to answer the question.", "example_cn": "轮到你回答这个问题了。"},
    ],
    "stop": [
        {"pos": "v.", "text": "停止", "example": "The rain stopped and the sun came out.", "example_cn": "雨停了，太阳出来了。"},
        {"pos": "n.", "text": "车站；停止", "example": "Get off the bus at the next stop.", "example_cn": "在下一站下车。"},
    ],
    "transport": [
        {"pos": "v.", "text": "运输", "example": "Trucks transport food to the city every day.", "example_cn": "卡车每天把食物运到城里。"},
        {"pos": "n.", "text": "交通；运输", "example": "Public transport is cheap in Beijing.", "example_cn": "北京的公共交通很便宜。"},
    ],
    "park": [
        {"pos": "n.", "text": "公园", "example": "Children like playing in the park on weekends.", "example_cn": "孩子们周末喜欢在公园玩。"},
        {"pos": "v.", "text": "停车", "example": "You can't park your car in front of the school gate.", "example_cn": "你不能把车停在校门口。"},
    ],
    "shop": [
        {"pos": "n.", "text": "商店", "example": "There is a small shop near our school.", "example_cn": "我们学校附近有一家小商店。"},
        {"pos": "v.", "text": "购物", "example": "My mother likes to shop online.", "example_cn": "我妈妈喜欢网上购物。"},
    ],
    "cost": [
        {"pos": "v.", "text": "花费", "example": "The new dictionary cost me fifty yuan.", "example_cn": "这本新词典花了我五十元。"},
        {"pos": "n.", "text": "费用，成本", "example": "The cost of the school trip is not high.", "example_cn": "这次学校旅行的费用不高。"},
    ],
    "change": [
        {"pos": "n.", "text": "零钱；变化", "example": "Keep the change, please.", "example_cn": "零钱不用找了。"},
        {"pos": "v.", "text": "改变；更换", "example": "We should change our bad habits.", "example_cn": "我们应该改掉坏习惯。"},
    ],
    "bargain": [
        {"pos": "v.", "text": "讨价还价", "example": "She likes to bargain when she buys clothes.", "example_cn": "她买衣服时喜欢讨价还价。"},
        {"pos": "n.", "text": "便宜货；交易", "example": "This coat is a real bargain.", "example_cn": "这件外套真便宜。"},
    ],
    "list": [
        {"pos": "n.", "text": "清单", "example": "Please make a list of the things you need.", "example_cn": "请把你需要的东西列成清单。"},
        {"pos": "v.", "text": "列出", "example": "The teacher listed three reasons in the passage.", "example_cn": "老师在短文中列出了三个理由。"},
    ],
    "order": [
        {"pos": "n.", "text": "订单；顺序", "example": "Put the sentences in the right order.", "example_cn": "把句子按正确顺序排列。"},
        {"pos": "v.", "text": "订购；命令", "example": "We ordered some books from the school shop.", "example_cn": "我们从学校商店订了一些书。"},
    ],
    "cough": [
        {"pos": "n.", "text": "咳嗽", "example": "He has had a bad cough for a week.", "example_cn": "他已经咳嗽一周了。"},
        {"pos": "v.", "text": "咳嗽", "example": "Cover your mouth when you cough.", "example_cn": "咳嗽时要捂住嘴。"},
    ],
    "exercise": [
        {"pos": "n.", "text": "锻炼；练习", "example": "Doing exercise every day is good for your health.", "example_cn": "每天锻炼有益健康。"},
        {"pos": "v.", "text": "锻炼", "example": "We exercise on the playground after class.", "example_cn": "课后我们在操场锻炼。"},
    ],
    "rest": [
        {"pos": "n.", "text": "休息", "example": "You need a good rest after the long trip.", "example_cn": "长途旅行后你需要好好休息。"},
        {"pos": "v.", "text": "休息", "example": "Let's rest under the tree for a while.", "example_cn": "我们在树下休息一会儿吧。"},
    ],
    "sleep": [
        {"pos": "v.", "text": "睡觉", "example": "Students should sleep at least eight hours a night.", "example_cn": "学生每晚至少应睡八小时。"},
        {"pos": "n.", "text": "睡眠", "example": "A good sleep helps you study better.", "example_cn": "良好的睡眠有助于学习。"},
    ],
    "rain": [
        {"pos": "n.", "text": "雨", "example": "The heavy rain made the roads dangerous.", "example_cn": "大雨让道路变得危险。"},
        {"pos": "v.", "text": "下雨", "example": "It often rains in Beijing in July.", "example_cn": "北京七月经常下雨。"},
    ],
    "snow": [
        {"pos": "n.", "text": "雪", "example": "The children played in the snow after school.", "example_cn": "孩子们放学后在雪地里玩。"},
        {"pos": "v.", "text": "下雪", "example": "It snowed heavily last night.", "example_cn": "昨晚下了大雪。"},
    ],
    "plastic": [
        {"pos": "n.", "text": "塑料", "example": "We should use less plastic to protect the earth.", "example_cn": "为了保护地球，我们应该少用塑料。"},
        {"pos": "adj.", "text": "塑料的", "example": "Don't throw plastic bags into the river.", "example_cn": "不要把塑料袋扔进河里。"},
    ],
    "clean": [
        {"pos": "adj.", "text": "干净的", "example": "Keep the classroom clean every day.", "example_cn": "每天保持教室干净。"},
        {"pos": "v.", "text": "打扫，清洁", "example": "We clean our classroom after school.", "example_cn": "放学后我们打扫教室。"},
    ],
    "play": [
        {"pos": "v.", "text": "玩；打球；演奏", "example": "They play football on the playground after class.", "example_cn": "课后他们在操场踢足球。"},
        {"pos": "n.", "text": "戏剧；玩耍", "example": "Our class will put on a play next week.", "example_cn": "我们班下周将上演一出戏剧。"},
    ],
    "practice": [
        {"pos": "n.", "text": "练习", "example": "Practice makes perfect.", "example_cn": "熟能生巧。"},
        {"pos": "v.", "text": "练习", "example": "She practices the piano for an hour every day.", "example_cn": "她每天练一小时钢琴。"},
    ],
    "score": [
        {"pos": "n.", "text": "得分；分数", "example": "Our team got a high score in the match.", "example_cn": "我们队在比赛中得了高分。"},
        {"pos": "v.", "text": "得分", "example": "He scored two goals in the last five minutes.", "example_cn": "他在最后五分钟进了两球。"},
    ],
    "dance": [
        {"pos": "v.", "text": "跳舞", "example": "The students danced happily at the school party.", "example_cn": "学生们在学校晚会上开心地跳舞。"},
        {"pos": "n.", "text": "舞蹈", "example": "She is taking a dance class this term.", "example_cn": "这学期她在上舞蹈课。"},
    ],
    "interest": [
        {"pos": "n.", "text": "兴趣", "example": "He shows a great interest in science.", "example_cn": "他对科学表现出浓厚兴趣。"},
        {"pos": "v.", "text": "使感兴趣", "example": "The story interested all the students in class.", "example_cn": "这个故事让全班同学都感兴趣。"},
    ],
    "cycle": [
        {"pos": "v.", "text": "骑行", "example": "Many students cycle to school to keep fit.", "example_cn": "许多学生骑车上学以保持健康。"},
        {"pos": "n.", "text": "循环；自行车", "example": "The water cycle is an important topic in science.", "example_cn": "水循环是科学课的重要主题。"},
    ],
    "stress": [
        {"pos": "n.", "text": "压力", "example": "Too much stress is bad for students' health.", "example_cn": "压力过大学生健康不利。"},
        {"pos": "v.", "text": "强调", "example": "The teacher stressed the importance of reading.", "example_cn": "老师强调了阅读的重要性。"},
    ],
    "hope": [
        {"pos": "v.", "text": "希望", "example": "I hope you will enjoy the school trip.", "example_cn": "我希望你会喜欢这次学校旅行。"},
        {"pos": "n.", "text": "希望", "example": "Never give up hope when you meet difficulties.", "example_cn": "遇到困难时永远不要放弃希望。"},
    ],
    "wish": [
        {"pos": "v.", "text": "希望；祝愿", "example": "I wish you good luck in the exam.", "example_cn": "祝你考试好运。"},
        {"pos": "n.", "text": "愿望", "example": "Her wish is to be a doctor in the future.", "example_cn": "她的愿望是将来当医生。"},
    ],
    "cry": [
        {"pos": "v.", "text": "哭；喊", "example": "The little boy began to cry when he got lost.", "example_cn": "小男孩迷路时哭了起来。"},
        {"pos": "n.", "text": "哭声；喊叫", "example": "We heard a cry for help from the river.", "example_cn": "我们听到河边有人呼救。"},
    ],
    "smile": [
        {"pos": "v.", "text": "微笑", "example": "She smiled and said hello to her classmates.", "example_cn": "她微笑着向同学问好。"},
        {"pos": "n.", "text": "微笑", "example": "A kind smile can make people feel warm.", "example_cn": "一个善意的微笑能让人感到温暖。"},
    ],
    "laugh": [
        {"pos": "v.", "text": "笑", "example": "The joke made the whole class laugh.", "example_cn": "这个笑话让全班都笑了。"},
        {"pos": "n.", "text": "笑声", "example": "We heard a loud laugh from the next room.", "example_cn": "我们听到隔壁房间传来大笑声。"},
    ],
    "online": [
        {"pos": "adj.", "text": "在线的", "example": "More students are taking online classes now.", "example_cn": "现在更多学生在上在线课程。"},
        {"pos": "adv.", "text": "在线地", "example": "You can look up new words online.", "example_cn": "你可以在网上查新单词。"},
    ],
    "today": [
        {"pos": "n.", "text": "今天", "example": "Today is Monday, so we have a Chinese class.", "example_cn": "今天是星期一，所以我们有语文课。"},
        {"pos": "adv.", "text": "在今天", "example": "We have a math test today.", "example_cn": "我们今天有数学测验。"},
    ],
    "tomorrow": [
        {"pos": "n.", "text": "明天", "example": "Tomorrow is the first day of the school trip.", "example_cn": "明天是学校旅行的第一天。"},
        {"pos": "adv.", "text": "在明天", "example": "We will visit the museum tomorrow.", "example_cn": "我们明天将参观博物馆。"},
    ],
    "yesterday": [
        {"pos": "n.", "text": "昨天", "example": "Yesterday was my first day at the new school.", "example_cn": "昨天是我在新学校的第一天。"},
        {"pos": "adv.", "text": "在昨天", "example": "I finished my homework yesterday.", "example_cn": "我昨天完成了作业。"},
    ],
    "past": [
        {"pos": "n.", "text": "过去", "example": "We can learn a lot from the past.", "example_cn": "我们可以从过去学到很多。"},
        {"pos": "adj.", "text": "过去的", "example": "In the past few years, Beijing has changed a lot.", "example_cn": "过去几年北京变化很大。"},
    ],
    "early": [
        {"pos": "adj.", "text": "早的", "example": "He is always an early bird at school.", "example_cn": "他在学校总是很早到。"},
        {"pos": "adv.", "text": "早地", "example": "Please come to school early tomorrow.", "example_cn": "请明天早点到校。"},
    ],
    "late": [
        {"pos": "adj.", "text": "迟的，晚的", "example": "Don't be late for the English exam.", "example_cn": "英语考试不要迟到。"},
        {"pos": "adv.", "text": "晚地", "example": "She arrived late because of the heavy rain.", "example_cn": "因为大雨她迟到了。"},
    ],
    "before": [
        {"pos": "prep.", "text": "在……之前", "example": "Please wash your hands before meals.", "example_cn": "饭前请洗手。"},
        {"pos": "adv.", "text": "以前", "example": "I have never seen this word before.", "example_cn": "我以前从未见过这个词。"},
    ],
    "after": [
        {"pos": "prep.", "text": "在……之后", "example": "We play basketball after school.", "example_cn": "放学后我们打篮球。"},
        {"pos": "adv.", "text": "后来", "example": "He left, and I never saw him after.", "example_cn": "他离开后我再也没见过他。"},
    ],
    "kind": [
        {"pos": "adj.", "text": "善良的，友好的", "example": "Our English teacher is kind to every student.", "example_cn": "我们的英语老师对每个学生都很友善。"},
        {"pos": "n.", "text": "种类", "example": "What kind of books do you like reading?", "example_cn": "你喜欢读哪一类书？"},
    ],
    "help": [
        {"pos": "v.", "text": "帮助", "example": "Could you help me with this math problem?", "example_cn": "你能帮我做这道数学题吗？"},
        {"pos": "n.", "text": "帮助", "example": "Thank you for your help.", "example_cn": "谢谢你的帮助。"},
    ],
    "thank": [
        {"pos": "v.", "text": "感谢", "example": "I want to thank my teachers for their help.", "example_cn": "我想感谢老师们的帮助。"},
        {"pos": "n.", "text": "感谢（常用 thanks）", "example": "Many thanks for your kind letter.", "example_cn": "非常感谢你亲切的来信。"},
    ],
    "respect": [
        {"pos": "v.", "text": "尊重", "example": "We should respect our parents and teachers.", "example_cn": "我们应该尊重父母和老师。"},
        {"pos": "n.", "text": "尊重", "example": "He is a man of great respect in our school.", "example_cn": "他在我们学校很受尊敬。"},
    ],
    "trust": [
        {"pos": "v.", "text": "信任", "example": "I trust my best friend with my secrets.", "example_cn": "我把秘密告诉最好的朋友。"},
        {"pos": "n.", "text": "信任", "example": "Trust is important between friends.", "example_cn": "朋友之间信任很重要。"},
    ],
    "exchange": [
        {"pos": "v.", "text": "交换", "example": "We exchanged gifts at the New Year party.", "example_cn": "我们在新年晚会上交换了礼物。"},
        {"pos": "n.", "text": "交换；交流", "example": "The school has an exchange program with a school in the UK.", "example_cn": "学校与英国一所学校有交流项目。"},
    ],
    "volunteer": [
        {"pos": "n.", "text": "志愿者", "example": "Many volunteers helped at the sports meeting.", "example_cn": "许多志愿者在运动会上帮忙。"},
        {"pos": "v.", "text": "自愿做", "example": "She volunteered to clean the classroom.", "example_cn": "她自愿打扫教室。"},
    ],
    "welcome": [
        {"pos": "v.", "text": "欢迎", "example": "We welcome new students to our class.", "example_cn": "我们欢迎新同学来到我们班。"},
        {"pos": "adj.", "text": "受欢迎的", "example": "You are always welcome in our school.", "example_cn": "你在我们学校永远受欢迎。"},
    ],
    "promise": [
        {"pos": "v.", "text": "承诺", "example": "He promised to finish the homework on time.", "example_cn": "他答应按时完成作业。"},
        {"pos": "n.", "text": "承诺", "example": "Keep your promise if you make one.", "example_cn": "许下承诺就要遵守。"},
    ],
    "plant": [
        {"pos": "n.", "text": "植物", "example": "Green plants can make the air cleaner.", "example_cn": "绿色植物能让空气更清新。"},
        {"pos": "v.", "text": "种植", "example": "We planted trees on the hill last spring.", "example_cn": "去年春天我们在山上种了树。"},
    ],
    "square": [
        {"pos": "n.", "text": "正方形；广场", "example": "People like walking in the square after dinner.", "example_cn": "人们晚饭后喜欢在广场散步。"},
        {"pos": "adj.", "text": "正方形的", "example": "Draw a square on your paper.", "example_cn": "在纸上画一个正方形。"},
    ],
    "light": [
        {"pos": "n.", "text": "光；灯", "example": "Turn off the light when you leave the room.", "example_cn": "离开房间时请关灯。"},
        {"pos": "adj.", "text": "轻的；浅的", "example": "This bag is light enough for a child to carry.", "example_cn": "这个包很轻，小孩也拿得动。"},
    ],
    "watch": [
        {"pos": "v.", "text": "观看", "example": "We watched a science film in class yesterday.", "example_cn": "昨天我们在课上看了一部科学电影。"},
        {"pos": "n.", "text": "手表", "example": "My father gave me a watch on my birthday.", "example_cn": "爸爸在我生日时送了我一块手表。"},
    ],
    "dress": [
        {"pos": "n.", "text": "连衣裙", "example": "She wore a red dress to the school party.", "example_cn": "她穿着红裙子去参加学校晚会。"},
        {"pos": "v.", "text": "穿衣", "example": "The little girl can dress herself now.", "example_cn": "小女孩现在能自己穿衣服了。"},
    ],
    "chinese": [
        {"pos": "n.", "text": "汉语；语文；中国人", "example": "Chinese is one of the most important subjects at school.", "example_cn": "语文是学校最重要的科目之一。"},
        {"pos": "adj.", "text": "中国的", "example": "We are proud of Chinese culture.", "example_cn": "我们为中国文化感到自豪。"},
    ],
    "american": [
        {"pos": "adj.", "text": "美国的", "example": "He has an American friend in his class.", "example_cn": "他班上有一位美国朋友。"},
        {"pos": "n.", "text": "美国人", "example": "The American visited our school last week.", "example_cn": "那位美国人上周参观了我们学校。"},
    ],
    "english": [
        {"pos": "n.", "text": "英语", "example": "English is widely used in the world.", "example_cn": "英语在世界上被广泛使用。"},
        {"pos": "adj.", "text": "英国的；英语的", "example": "We have an English class every morning.", "example_cn": "我们每天上午都有英语课。"},
    ],
    "native": [
        {"pos": "adj.", "text": "本地的；本国的", "example": "Chinese is my native language.", "example_cn": "汉语是我的母语。"},
        {"pos": "n.", "text": "本地人", "example": "The natives were friendly to the visitors.", "example_cn": "当地人对游客很友好。"},
    ],
    "french": [
        {"pos": "adj.", "text": "法国的", "example": "She likes French food very much.", "example_cn": "她非常喜欢法国食物。"},
        {"pos": "n.", "text": "法语；法国人", "example": "He is learning French after school.", "example_cn": "他放学后在学法语。"},
    ],
    "japanese": [
        {"pos": "adj.", "text": "日本的", "example": "We visited a Japanese garden in the park.", "example_cn": "我们在公园里参观了一座日式庭园。"},
        {"pos": "n.", "text": "日语；日本人", "example": "Can you speak Japanese?", "example_cn": "你会说日语吗？"},
    ],
    "start": [
        {"pos": "v.", "text": "开始", "example": "The exam will start at 9:00 in the morning.", "example_cn": "考试将在上午九点开始。"},
        {"pos": "n.", "text": "开始", "example": "A good start is half the battle.", "example_cn": "好的开始是成功的一半。"},
    ],
    "use": [
        {"pos": "v.", "text": "使用", "example": "We can use a dictionary to look up new words.", "example_cn": "我们可以用词典查新单词。"},
        {"pos": "n.", "text": "用途；使用", "example": "This tool has many uses in daily life.", "example_cn": "这个工具在日常生活中有许多用途。"},
    ],
    "need": [
        {"pos": "v.", "text": "需要", "example": "You need to read the questions carefully.", "example_cn": "你需要仔细阅读题目。"},
        {"pos": "n.", "text": "需要", "example": "There is no need to worry about the test.", "example_cn": "不必为考试担心。"},
    ],
    "show": [
        {"pos": "v.", "text": "展示；表明", "example": "The picture shows a busy street in Beijing.", "example_cn": "这幅图展示了北京一条繁忙的街道。"},
        {"pos": "n.", "text": "演出；展览", "example": "There will be a talent show in our school.", "example_cn": "我们学校将有一场才艺表演。"},
    ],
    "look": [
        {"pos": "v.", "text": "看；看起来", "example": "Look at the blackboard, please.", "example_cn": "请看黑板。"},
        {"pos": "n.", "text": "外表；神情", "example": "She had a worried look on her face.", "example_cn": "她脸上露出担心的神情。"},
    ],
    "talk": [
        {"pos": "v.", "text": "谈话", "example": "Don't talk in the reading room.", "example_cn": "阅览室里不要交谈。"},
        {"pos": "n.", "text": "谈话；演讲", "example": "The head teacher gave a talk about safety.", "example_cn": "校长做了一次关于安全的讲话。"},
    ],
    "open": [
        {"pos": "v.", "text": "打开", "example": "Please open your books at page 20.", "example_cn": "请把书翻到第20页。"},
        {"pos": "adj.", "text": "开着的；开放的", "example": "The library is open from 8:00 to 17:00.", "example_cn": "图书馆从8点开到17点。"},
    ],
    "close": [
        {"pos": "v.", "text": "关闭", "example": "Please close the window. It's cold outside.", "example_cn": "请关上窗户，外面很冷。"},
        {"pos": "adj.", "text": "近的；亲密的", "example": "The supermarket is close to our school.", "example_cn": "超市离我们学校很近。"},
    ],
    "work": [
        {"pos": "v.", "text": "工作；起作用", "example": "My mother works in a hospital.", "example_cn": "我妈妈在医院工作。"},
        {"pos": "n.", "text": "工作；作业", "example": "Hard work leads to success.", "example_cn": "努力工作通向成功。"},
    ],
    "first": [
        {"pos": "adj.", "text": "第一的", "example": "Monday is the first day of the school week.", "example_cn": "星期一是学校一周的第一天。"},
        {"pos": "adv.", "text": "首先", "example": "First, read the passage; then answer the questions.", "example_cn": "首先读短文，然后回答问题。"},
    ],
    "last": [
        {"pos": "adj.", "text": "最后的；上一个的", "example": "I saw him last week in the library.", "example_cn": "我上周在图书馆见到他。"},
        {"pos": "adv.", "text": "最后", "example": "Who spoke last at the meeting?", "example_cn": "谁在会上最后发言？"},
    ],
    "most": [
        {"pos": "adv.", "text": "最", "example": "This is the most interesting book I have ever read.", "example_cn": "这是我读过的最有趣的书。"},
        {"pos": "adj.", "text": "大多数的", "example": "Most students in our class like PE.", "example_cn": "我们班大多数学生喜欢体育。"},
    ],
    "much": [
        {"pos": "adv.", "text": "非常；更加", "example": "Thank you very much for your help.", "example_cn": "非常感谢你的帮助。"},
        {"pos": "adj.", "text": "许多（不可数）", "example": "There isn't much time left for the exam.", "example_cn": "考试剩下的时间不多了。"},
    ],
    "all": [
        {"pos": "pron.", "text": "全部", "example": "All of the students passed the test.", "example_cn": "所有学生都通过了测验。"},
        {"pos": "adj.", "text": "全部的", "example": "All the lights in the classroom were on.", "example_cn": "教室里所有的灯都开着。"},
    ],
    "some": [
        {"pos": "adj.", "text": "一些", "example": "I need some paper to write on.", "example_cn": "我需要一些纸来写字。"},
        {"pos": "pron.", "text": "一些", "example": "Some of the questions are easy.", "example_cn": "有些题目很容易。"},
    ],
    "any": [
        {"pos": "adj.", "text": "任何的；一些（疑问/否定）", "example": "Do you have any questions about the text?", "example_cn": "关于课文你有什么问题吗？"},
        {"pos": "pron.", "text": "任何；一些", "example": "If any of you need help, please raise your hand.", "example_cn": "如果你们谁需要帮助，请举手。"},
    ],
    "no": [
        {"pos": "adv.", "text": "不", "example": "No, I don't agree with that idea.", "example_cn": "不，我不同意那个想法。"},
        {"pos": "adj.", "text": "没有的", "example": "There is no water in the bottle.", "example_cn": "瓶子里没有水。"},
    ],
    "when": [
        {"pos": "conj.", "text": "当……时", "example": "When the bell rang, the students ran out.", "example_cn": "铃响时学生们跑了出去。"},
        {"pos": "adv.", "text": "什么时候", "example": "When did you finish your homework?", "example_cn": "你什么时候做完作业的？"},
    ],
    "which": [
        {"pos": "pron.", "text": "哪一个", "example": "Which of the three answers is right?", "example_cn": "三个答案中哪一个是对的？"},
        {"pos": "adj.", "text": "哪一个的", "example": "Which book do you want to borrow?", "example_cn": "你想借哪一本书？"},
    ],
    "about": [
        {"pos": "prep.", "text": "关于", "example": "This passage is about a famous scientist.", "example_cn": "这篇短文是关于一位著名科学家的。"},
        {"pos": "adv.", "text": "大约", "example": "The museum is about two kilometers from here.", "example_cn": "博物馆离这里大约两公里。"},
    ],
    "class": [
        {"pos": "n.", "text": "班级；课", "example": "There are forty students in our class.", "example_cn": "我们班有四十名学生。"},
    ],
    "book": [
        {"pos": "n.", "text": "书；本子", "example": "This book is about the history of Beijing.", "example_cn": "这本书是关于北京历史的。"},
    ],
    "grade": [
        {"pos": "n.", "text": "年级；分数", "example": "My sister is in Grade 8 this year.", "example_cn": "我妹妹今年上八年级。"},
    ],
    "subject": [
        {"pos": "n.", "text": "学科，科目", "example": "English is my favorite subject at school.", "example_cn": "英语是我在学校最喜欢的科目。"},
    ],
}

COLOR_WORDS = {
    "red", "blue", "green", "yellow", "black", "white", "brown",
    "orange", "purple", "pink", "gray", "grey",
}


def split_pos_list(pos: str) -> List[str]:
    raw = (pos or "").strip()
    if not raw:
        return [""]
    parts = [p.strip() for p in re.split(r"\s*/\s*", raw) if p.strip()]
    out: List[str] = []
    for p in parts:
        if p.endswith(".") or p in {"aux", "aux."}:
            out.append(p if p.endswith(".") else "aux.")
        else:
            out.append(p + ".")
    return out or [raw]


def split_gloss_list(meaning: str, n_pos: int) -> List[str]:
    text = (meaning or "").strip()
    if not text:
        return [""]
    for sep in ("；", ";"):
        parts = [x.strip() for x in text.split(sep) if x.strip()]
        if len(parts) >= 2:
            return parts
    if n_pos >= 2:
        for sep in ("，", ","):
            parts = [x.strip() for x in text.split(sep) if x.strip()]
            if len(parts) == n_pos:
                return parts
    return [text]


def _pair_senses(pos_list: List[str], glosses: List[str]) -> List[Dict[str, str]]:
    if len(pos_list) == 1 and len(glosses) > 1:
        return [{"pos": pos_list[0], "text": g} for g in glosses]
    if len(glosses) == 1 and len(pos_list) > 1:
        return [{"pos": p, "text": glosses[0]} for p in pos_list]
    n = max(len(pos_list), len(glosses))
    out = []
    for i in range(n):
        out.append(
            {
                "pos": pos_list[i] if i < len(pos_list) else pos_list[-1],
                "text": glosses[i] if i < len(glosses) else glosses[-1],
            }
        )
    return out


def _scene_hint(scene: str) -> str:
    s = (scene or "").split()[0] if scene else ""
    return s or "校园生活"


FAMILY_PEOPLE = {
    "father", "mother", "parent", "parents", "brother", "sister", "son", "daughter",
    "grandfather", "grandmother", "grandparents", "uncle", "aunt", "cousin",
    "husband", "wife", "child", "baby", "kid", "family", "relative", "neighbor",
}


def _is_generic_example(ex: str) -> bool:
    s = (ex or "").strip()
    return (
        s.startswith("There is a ")
        or s.startswith("I want to ")
        or s.startswith("It looks very ")
        or s.startswith("Students often talk about the ")
        or s.startswith("Every family has a ")
        or "every day to make progress at school" in s
    )


SCHOOL_NOUN_EXAMPLES = {
    "homework": ("Please finish your homework before you watch TV.", "请在看电视前完成家庭作业。"),
    "textbook": ("Please take out your textbook and turn to page 20.", "请拿出课本翻到第20页。"),
    "workbook": ("We will check the workbook in the next class.", "下节课我们要核对练习册。"),
    "pencil": ("I need a pencil to write down the new words.", "我需要一支铅笔来记下这些新单词。"),
    "eraser": ("May I use your eraser for a minute?", "我可以用一下你的橡皮吗？"),
    "playground": ("The students play football on the playground after class.", "课后学生们在操场踢足球。"),
    "classroom": ("Keep quiet in the classroom during the exam.", "考试时请在教室里保持安静。"),
    "blackboard": ("The teacher wrote the new words on the blackboard.", "老师把新单词写在黑板上。"),
    "notebook": ("Write the key points in your notebook.", "把要点记在笔记本上。"),
    "schoolbag": ("He put the books into his schoolbag.", "他把书放进书包里。"),
    "ruler": ("Use a ruler to draw a straight line.", "用尺子画一条直线。"),
    "dictionary": ("You can look up the new word in a dictionary.", "你可以在词典里查这个新单词。"),
}


def _fallback_example(word: str, pos: str, gloss: str, scene: str) -> tuple[str, str]:
    w = word
    hint = _scene_hint(scene)
    p = (pos or "n.").lower()
    g = (gloss or w).split("；")[0].split("，")[0].strip() or w
    key = w.lower()
    if key in SCHOOL_NOUN_EXAMPLES:
        return SCHOOL_NOUN_EXAMPLES[key]
    if key in COLOR_WORDS:
        return (
            f"She wore a {w} T-shirt on the school sports day.",
            f"校运会那天她穿了一件{g}的T恤。",
        )
    if key in FAMILY_PEOPLE:
        return (
            f"My {w} often helps me with my homework.",
            f"我的{g}经常帮我做作业。",
        )
    if p.startswith("v"):
        return (
            f"The teacher asked us to {w} in class.",
            f"老师让我们在课堂上{g}。",
        )
    if p.startswith("adj"):
        return (
            f"It is {w} for students to help each other at school.",
            f"在学校里互相帮助是{g}的。",
        )
    if p.startswith("adv"):
        return (
            f"Please listen {w} when the teacher explains the text.",
            f"老师讲解课文时请{g}听。",
        )
    if p.startswith("prep"):
        return (
            f"The library is {w} the classroom building.",
            f"图书馆在教学楼{g}。",
        )
    if p.startswith("conj"):
        return (
            f"We stayed at school {w} it began to rain.",
            f"我们留在学校，{g}开始下雨了。",
        )
    if p.startswith("pron"):
        return (
            f"{w.capitalize()} of the students finished the paper on time.",
            f"{g}按时完成了试卷。",
        )
    if hint.startswith("学校"):
        return (f"We often use {w} in our school life.", f"我们在校园生活中经常用到{g}。")
    if hint.startswith("家庭"):
        return (f"We often talk about {w} at home.", f"我们在家里经常谈到{g}。")
    if hint.startswith("饮食"):
        return (f"We had {w} for lunch at the school dining hall.", f"我们在学校食堂午餐吃了{g}。")
    if hint.startswith("交通"):
        return (f"You can take a {w} to get to the museum.", f"你可以乘坐{g}去博物馆。")
    if hint.startswith("购物"):
        return (f"I bought a {w} in the supermarket.", f"我在超市买了{g}。")
    if hint.startswith("医疗") or hint.startswith("身体"):
        return (f"The doctor asked me about my {w}.", f"医生问起了我的{g}。")
    if hint.startswith("自然") or hint.startswith("动物"):
        return (f"We learned about the {w} in the science class.", f"我们在科学课上了解了{g}。")
    if hint.startswith("体育"):
        return (f"The {w} is popular among students after class.", f"课后同学们很喜欢{g}。")
    if hint.startswith("科技"):
        return (f"The {w} makes our study easier than before.", f"{g}让我们的学习比以前更容易。")
    if hint.startswith("时间"):
        return (f"Please remember the {w} of the exam.", f"请记住考试的{g}。")
    if hint.startswith("节假"):
        return (f"We enjoyed the {w} during the holiday.", f"假期里我们很享受{g}。")
    return (f"The {w} in the passage is important for the students.", f"短文中的{g}对学生很重要。")


def build_senses(
    word: str,
    pos: str = "",
    meaning: str = "",
    example: str = "",
    scene: str = "",
    meanings: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, str]]:
    key = (word or "").lower()
    bank = SENSE_BANK.get(key)
    if bank:
        pairs = [{"pos": x.get("pos") or "", "text": x.get("text") or meaning} for x in bank]
    else:
        pos_list = split_pos_list(pos)
        if meanings:
            glosses = [str(m.get("text") or "").strip() for m in meanings if str(m.get("text") or "").strip()]
            raw_pos = [str(m.get("pos") or "").strip() for m in meanings]
            if any("/" in p for p in raw_pos) or len(set(p for p in raw_pos if p)) <= 1:
                glosses = split_gloss_list(meaning or "；".join(glosses), len(pos_list))
                pairs = _pair_senses(pos_list, glosses)
            else:
                pairs = [{"pos": (m.get("pos") or pos), "text": str(m.get("text") or "")} for m in meanings]
        else:
            pairs = _pair_senses(pos_list, split_gloss_list(meaning, len(pos_list)))

    out: List[Dict[str, str]] = []
    used_ids: List[int] = []
    shared_exam: dict | None = None
    for i, pair in enumerate(pairs):
        src = meanings[i] if meanings and i < len(meanings) and isinstance(meanings[i], dict) else {}
        hits = lookup_exam_examples(word, pair["pos"], limit=4, used_ids=used_ids)
        if not hits:
            # 词性对不上时，仍用含该词的真题句，避免改用自造句
            hits = lookup_exam_examples(word, "", limit=4, used_ids=used_ids)
        if not hits:
            hits = lookup_exam_examples(word, pair["pos"] or "", limit=4, used_ids=[])
        picked = hits[0] if hits else None
        if picked:
            used_ids.append(int(picked["id"]))
            if shared_exam is None:
                shared_exam = picked
            ex, cn = picked["en"], picked["cn"]
            src_label = picked.get("source") or ""
        elif shared_exam:
            ex, cn = shared_exam["en"], shared_exam["cn"]
            src_label = shared_exam.get("source") or ""
        else:
            bank_item = bank[i] if bank and i < len(bank) else {}
            ex = str(bank_item.get("example") or src.get("example") or "")
            cn = str(bank_item.get("example_cn") or src.get("example_cn") or "")
            src_label = str(bank_item.get("source") or src.get("source") or "")
            if not src_label or _is_generic_example(ex) or not ex:
                ex, cn = _fallback_example(word, pair["pos"], pair["text"], scene)
                src_label = ""
        out.append(
            {
                "pos": pair["pos"],
                "text": pair["text"],
                "example": ex,
                "example_cn": cn,
                "source": src_label,
            }
        )
    return out


def enrich_item(item: Dict[str, Any]) -> Dict[str, Any]:
    senses = build_senses(
        word=str(item.get("word") or ""),
        pos=str(item.get("pos") or ""),
        meaning=str(item.get("meaning") or ""),
        example=str(item.get("example") or ""),
        scene=str(item.get("scene") or ""),
        meanings=item.get("meanings") if isinstance(item.get("meanings"), list) else None,
    )
    item = dict(item)
    item["meanings"] = senses
    item["example"] = senses[0]["example"] if senses else item.get("example") or ""
    item["pos"] = "/".join(dict.fromkeys(s["pos"] for s in senses if s.get("pos"))) or item.get("pos") or ""
    return item
