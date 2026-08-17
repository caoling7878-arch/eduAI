from __future__ import annotations

"""中考英语真题短句语料（2015–2026，含北京及近十年全国卷）。短句摘自公开真题，供背单词例句检索。"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"])")
_ABBR = re.compile(r"\b(Mr|Mrs|Ms|Dr|Prof|St|No|vs|U\.S)\.", re.I)


def _split_sentences(text: str) -> List[str]:
    protected = _ABBR.sub(lambda m: m.group(0).replace(".", "<DOT>"), text)
    parts = [_clean(p.replace("<DOT>", ".")) for p in _SPLIT.split(protected) if _clean(p)]
    merged: List[str] = []
    for p in parts:
        if merged and (
            p[:1].islower()
            or merged[-1].rstrip(".").endswith(("Mr", "Mrs", "Ms", "Dr", "Prof"))
        ):
            merged[-1] = f"{merged[-1].rstrip('.')} {p}".strip()
        else:
            merged.append(p)
    return merged


def _clean(text: str) -> str:
    t = (text or "").replace("\u3000", " ").replace("——", "—")
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" ,", ",").replace(" .", ".")
    return t


def _add(
    rows: List[dict],
    year: int,
    section: str,
    en: str,
    cn: str = "",
    place: str = "北京",
) -> None:
    en = _clean(en)
    cn = (cn or "").strip()
    if len(en) < 12:
        return
    # 去掉题号残留
    en = re.sub(r"^\d+\.\s*", "", en)
    en = en.replace("______", "").replace("___", "")
    en = re.sub(r"\s+", " ", en).strip(" -")
    if not en.endswith((".", "!", "?", "”", '"')):
        en = en.rstrip(".,;:") + "."
    rows.append({"year": year, "section": section, "en": en, "cn": cn, "place": place or "北京"})


def _split_passage(
    year: int,
    section: str,
    text: str,
    zh: Dict[str, str] | None = None,
    place: str = "北京",
) -> List[dict]:
    rows: List[dict] = []
    body = _clean(text)
    zh = zh or {}
    for p in _split_sentences(body):
        cn = ""
        for k, v in zh.items():
            if k.lower() in p.lower():
                cn = v
                break
        _add(rows, year, section, p, cn, place=place)
    return rows


def _build() -> List[dict]:
    rows: List[dict] = []

    # —— 单项填空（填入正确答案后的完整真题句）——
    grammar = [
        (2018, "My brother and I like football. We play it together once a week.", "我和哥哥都喜欢足球。我们每周一起踢一次。"),
        (2018, "Happy birthday, Peter! Here's a gift for you.", "彼得，生日快乐！这是给你的礼物。"),
        (2018, "How do you usually go to school, Mary? By bike.", "玛丽，你通常怎么去学校？骑自行车。"),
        (2018, "Many people like pandas because they are cute.", "许多人喜欢熊猫，因为它们很可爱。"),
        (2018, "I must go now, or I'll miss my train.", "我必须现在走，否则会赶不上火车。"),
        (2018, "Tony is the youngest of the three boys, but he is the tallest.", "托尼是三个男孩中最小的，但他最高。"),
        (2018, "Bill likes reading. He reads picture books with his dad every evening.", "比尔喜欢阅读。他每天晚上和爸爸一起看图画书。"),
        (2018, "Paul, what were you doing at nine last night? I was watching a movie in the cinema with my friends.", "保罗，昨晚九点你在做什么？我在电影院和朋友看电影。"),
        (2018, "David is a tennis player. He began to play tennis when he was six years old.", "大卫是网球运动员。他六岁开始打网球。"),
        (2018, "Lucy, is your uncle a teacher? Yes, he is. He has taught history for nearly 20 years.", "露西，你叔叔是老师吗？是的。他教历史快二十年了。"),
        (2018, "A new international airport will be completed in the city next year.", "这座城市明年将建成一座新的国际机场。"),
        (2018, "Alice, could you tell me when Mr. Smith left London? Sure. Last Sunday.", "爱丽丝，你能告诉我史密斯先生什么时候离开伦敦的吗？当然。上星期日。"),
        (2019, "Mr. Wang is coming to our school. I can't wait to see him.", "王老师要来我们学校。我迫不及待想见他。"),
        (2019, "We planted some flowers in the garden yesterday.", "昨天我们在花园里种了一些花。"),
        (2019, "Excuse me, how much is this T-shirt? It's 88 yuan.", "请问这件T恤多少钱？88元。"),
        (2019, "Lily, can you finish the letter in ten minutes? Yes, I can.", "莉莉，你能在十分钟内写完这封信吗？能。"),
        (2019, "This cap is nice, but it doesn't look good on me.", "这顶帽子不错，但戴在我头上不好看。"),
        (2019, "Julie takes good care of the family dog. She is more patient than her brother.", "朱莉把家里的狗照顾得很好。她比她哥哥更有耐心。"),
        (2019, "Sam skates with his friends every weekend.", "萨姆每个周末都和朋友一起滑冰。"),
        (2019, "Tom, what's your dad doing? He is repairing my bike.", "汤姆，你爸爸在干什么？他在修我的自行车。"),
        (2019, "Our school life has changed a lot since 2017. We have more activities now.", "自2017年以来我们的校园生活变了很多。现在我们有更多活动。"),
        (2019, "If you want to visit the Palace Museum, I will book tickets for you tomorrow.", "如果你想参观故宫，我明天就给你订票。"),
        (2019, "My advice on how to save paper was accepted by my class last Monday.", "上周一，我关于节约用纸的建议被全班采纳了。"),
        (2019, "Did you notice what Miss Lin was doing in her office? Yes. She was going over our writing.", "你注意到林老师在办公室做什么了吗？注意到了。她在批改我们的作文。"),
        (2021, "Mary's birthday is coming. We've decided to make a cake for her.", "玛丽的生日快到了。我们决定给她做蛋糕。"),
        (2021, "Space Day of China falls on April 24th every year.", "中国航天日在每年的4月24日。"),
        (2021, "Where shall we meet for the picnic? At the school gate.", "我们野餐在哪里集合？在学校门口。"),
        (2021, "Sam, can I join you in the community service? Of course you can.", "萨姆，我能和你一起参加社区服务吗？当然可以。"),
        (2021, "The doctors worked for ten hours, but nobody took a break.", "医生们工作了十个小时，但没有人休息。"),
        (2021, "The teacher is glad to see that Tony is more careful than before.", "老师很高兴看到托尼比以前更细心了。"),
        (2021, "Peter, what are you doing? Oh, I am writing a report about national heroes.", "彼得，你在做什么？我在写一篇关于民族英雄的报告。"),
        (2021, "My parents and I planted trees last Sunday.", "上周日我和父母一起种了树。"),
        (2021, "Lily, what do you usually do after school? I do exercise with my friends.", "莉莉，你放学后通常做什么？我和朋友一起锻炼。"),
        (2021, "Mr. Smith has learned Chinese for two years. He's much better at it now.", "史密斯先生学汉语两年了。他现在好多了。"),
        (2021, "Today, many winter Olympic sports are enjoyed even by children.", "如今，许多冬奥项目连孩子们都喜欢。"),
        (2021, "Could you please tell me when we will visit the Capital Museum? Next Thursday morning.", "你能告诉我我们什么时候参观首都博物馆吗？下周四上午。"),
        (2023, "My sister enjoys singing and her favorite subject is music.", "我姐姐喜欢唱歌，她最喜欢的科目是音乐。"),
        (2023, "It's a good idea to visit Beijing in October.", "十月去北京旅游是个好主意。"),
        (2023, "Must I stay here and wait for you? No, you needn't. You can go home now.", "我必须待在这里等你吗？不必。你现在可以回家。"),
        (2023, "Which do you like better, swimming or skating? Swimming.", "游泳和滑冰你更喜欢哪个？游泳。"),
        (2023, "How often do you tidy your own room? Twice a week.", "你多久整理一次自己的房间？一周两次。"),
        (2023, "It was difficult to climb the mountain, but Sam got to the top at last.", "爬山很难，但萨姆终于到了山顶。"),
        (2023, "Lucy, what are you doing? I am making a model ship.", "露西，你在做什么？我在做船模。"),
        (2023, "The Shenzhou-15 astronauts returned to Earth safely on June 4, 2023.", "神舟十五号航天员于2023年6月4日安全返回地球。"),
        (2023, "If you go to the concert with us tomorrow, you will have a great time there.", "如果你明天和我们去音乐会，你会玩得很开心。"),
        (2023, "Eric has learned many things since he became interested in science.", "埃里克对科学产生兴趣以来，已经学到了很多东西。"),
        (2023, "The park is getting more and more beautiful because more kinds of flowers are planted every year.", "公园越来越美，因为每年都会种更多种类的花。"),
        (2023, "Lily, can you tell me what you did during the Dragon Boat Festival this year? We ate zongzi and watched a dragon boat race.", "莉莉，你能告诉我今年端午节你们做了什么吗？我们吃了粽子，还看了龙舟赛。"),
        (2024, "My friends and I like sports. We often play basketball together after school.", "我和朋友们都喜欢运动。我们经常放学后一起打篮球。"),
        (2024, "The Chang'e-6 landed on the far side of the moon on June 2, 2024.", "嫦娥六号于2024年6月2日在月球背面着陆。"),
        (2024, "Bill, can I use your ruler? Of course you can. Here you are.", "比尔，我能用一下你的尺子吗？当然可以。给你。"),
        (2024, "What a lovely reading room! It's one of the nicest in our school.", "多好的阅览室啊！它是我们学校最棒的阅览室之一。"),
        (2024, "Lily, your new schoolbag is pretty. Where did you buy it? In a store near my home.", "莉莉，你的新书包真漂亮。你在哪儿买的？在我家附近的商店。"),
        (2024, "Hi, Mike! Would you like to go boating with me? Yes, I'd love to, but I have to finish my science project first.", "迈克，你想和我一起去划船吗？想，但我得先完成科学课题。"),
        (2024, "What did you do last Saturday, Tina? I went to the nursing home and worked as a volunteer there.", "蒂娜，上周六你做什么了？我去养老院做志愿者了。"),
        (2024, "A lot of people in China travel by high-speed train every year.", "每年都有很多人在中国乘坐高铁出行。"),
        (2024, "Amy, you didn't answer my call yesterday evening. Sorry, I didn't hear the ring. I was reading a book in my study.", "埃米，昨晚你没接我电话。对不起，我没听到铃声。我在书房看书。"),
        (2024, "With the help of my teacher, I have made much progress in English since last year.", "在老师的帮助下，从去年起我的英语有了很大进步。"),
        (2024, "Chinese is spoken by more and more people around the world these days.", "如今世界上越来越多的人说汉语。"),
        (2024, "Tim, do you know when we will hold the art festival? Sure! Next Friday.", "蒂姆，你知道我们什么时候举办艺术节吗？当然！下周五。"),
        (2025, "My sister is good at singing. She can even sing some French songs.", "我妹妹擅长唱歌。她甚至能唱一些法语歌。"),
        (2025, "These Chinese astronauts will stay in the space station for six months.", "这些中国航天员将在空间站停留六个月。"),
        (2025, "Mom, can I go to the cinema with my classmates this Sunday afternoon? Yes, of course you can.", "妈妈，这个星期天下午我能和同学去看电影吗？当然可以。"),
        (2025, "The National Library of China is the largest public library in Asia.", "中国国家图书馆是亚洲最大的公共图书馆。"),
        (2025, "Steve, when did you begin to learn how to play chess? About two years ago.", "史蒂夫，你什么时候开始学下棋的？大约两年前。"),
        (2025, "Janet has done a lot for us, so we want to write her a thank-you letter.", "珍妮特为我们做了很多，所以我们想给她写一封感谢信。"),
        (2025, "Mary was drawing a picture when her dad got home yesterday evening.", "昨天晚上爸爸到家时，玛丽正在画画。"),
        (2025, "Charlie visits his grandparents every weekend. He loves them very much.", "查理每个周末都去看望祖父母。他非常爱他们。"),
        (2025, "Peter, did you play table tennis with your friends after school yesterday? No, I didn't. We watered vegetables in our school garden.", "彼得，你昨天下课后和朋友打乒乓球了吗？没有。我们在学校菜园浇了菜。"),
        (2025, "Many international students have come to visit our school since last year.", "自去年以来，许多国际学生来参观我们学校。"),
        (2025, "Language learning apps are used by more and more people these days.", "如今越来越多的人使用语言学习应用程序。"),
        (2025, "Linda, do you know where we are going for the school trip this term? Yes. We are going to the Capital Museum.", "琳达，你知道这学期我们学校旅行去哪儿吗？知道。我们要去首都博物馆。"),
        (2026, "My father is a nature lover. His favourite activity is hiking in the forest.", "我父亲热爱自然。他最喜欢的活动是在森林里徒步。"),
        (2026, "Joe started to study Traditional Chinese Medicine at the age of 18.", "乔18岁开始学习中医。"),
        (2026, "The traffic laws say that everyone must wear the seat belt when travelling by car.", "交通法规规定，乘车时每个人都必须系安全带。"),
        (2026, "The Mid-Autumn Festival is one of the most popular festivals in China.", "中秋节是中国最受欢迎的节日之一。"),
        (2026, "How often do you visit the science museum? Once a month.", "你多久参观一次科学博物馆？一个月一次。"),
        (2026, "We lost the game, but we didn't lose hope in ourselves.", "我们输了比赛，但没有对自己失去希望。"),
        (2026, "The 'Reading Beijing' event draws thousands of students every year.", "“阅读北京”活动每年吸引成千上万名学生。"),
        (2026, "What is Dad doing in the study? He is working on his laptop.", "爸爸在书房做什么？他正在用笔记本电脑办公。"),
        (2026, "So far, they have had several meetings to discuss their plans for a field trip.", "到目前为止，他们已经开了好几次会来讨论实地考察计划。"),
        (2026, "Mum was cooking dinner for us when I got home from school.", "我从学校回到家时，妈妈正在为我们做晚饭。"),
        (2026, "A charity concert was held in the gym the day before yesterday.", "前天体育馆举办了一场慈善音乐会。"),
        (2026, "Could you tell me what we will do as volunteers tomorrow? Yes. We're going to clean up litter in the park.", "你能告诉我明天作为志愿者我们要做什么吗？可以。我们要去清理公园里的垃圾。"),
        (2020, "Mary, can you tell me where you bought the dictionary? Yes. I bought it in Xinhua Bookstore.", "玛丽，你能告诉我这本词典在哪里买的吗？可以。我在新华书店买的。"),
    ]
    for year, en, cn in grammar:
        _add(rows, year, "grammar", en, cn)

    # —— 完形填空（已按官方答案补全）——
    cloze = [
        (2017, "cloze",
         "Emily was an eighth grader. To pass her Civics course, she had to do some volunteer service in a nursing home for a week. "
         "One Monday, Emily went to the nursing home after school. When she arrived, she was told she would spend an hour every weekday with an elderly lady, Mrs. Blair. "
         "She was then led into a room, where an old lady in a flowery dress was sitting on a sofa. Emily stood awkwardly in front of the lady. "
         "She cleared her throat and said, Good afternoon. I'm Emily. Good afternoon, Emily. Take a seat, please. Mrs. Blair replied. "
         "Then, silence filled the space between them. Emily wondered what to say. Tell me about yourself, Emily, Mrs. Blair said suddenly. "
         "Well, Emily started, I don't have any grandparents, so I can't relate to elderly people much. I love the performing arts. "
         "I'm here mainly because I have to volunteer here to get a good grade for my Civics class. Mrs. Blair didn't seem to mind. "
         "Many people, especially teens, don't seem to care about old people like me. Now you're here, and I'm going to change that about you. Ask me anything. "
         "Emily thought for a moment, and finally decided, What was your job? I was a Broadway star in the 1950s. Mrs. Blair answered. "
         "Cool! Can you tell me about it? Emily asked, amazed. Mrs. Blair smiled. Back then, only the lead actress had the honor to wear a special bracelet. "
         "I was the lead in almost all of the plays, so I always wore the bracelet. Till this day, I still have it. "
         "Emily smiled along with Mrs. Blair and listened to the other stories, attentively. She had become so interested in Mrs. Blair's stories that she decided to come earlier the next day. "
         "Tuesday, Wednesday, and Thursday passed by quickly. Then came Friday. As she was leaving, Emily was really upset to say goodbye. "
         "Don't be sad. You can still visit me, Mrs. Blair comforted her. She then handed a small box to Emily. It's my gift to you. "
         "Emily carefully opened the box and was surprised to see what was inside. It's the bracelet that you wore. Thank you! Emily said, with tears in her eyes. "
         "I'm sure to visit you whenever I'm free. On her way home, Emily thought of her own love for the performing arts. She touched the bracelet and made a promise that she would keep her word to Mrs. Blair."),
        (2018, "cloze",
         "Thirty engineers were working as a team in a company. They were young and eager to learn. "
         "The management decided to teach them about finding real solutions to problems. "
         "One day, the team was called for a game in a hall. They were quite surprised and all reached the hall holding various thoughts. "
         "As they entered, they found a box placed in the center, full of flat balloons. The manager asked everyone to pick a balloon and blow it up. "
         "Then they were asked to write their names on their respective balloons carefully so that the balloons wouldn't blow out. "
         "All tried, but not everyone was successful. Five balloons blew out due to pressure. Those who failed to mark their names on the balloons were ruled out of the game. "
         "As a result, 25 engineers came to the next level. All the balloons carrying their names were collected and then put into a room, here and there. "
         "The engineers were told to pick the balloon with his or her name on. All the 25 engineers began to search for the respective balloons in a rush. "
         "It was almost 15 minutes but no one was able to find the right one. The second level of the game was over. "
         "Then came the final level. The engineers were asked to pick any balloon and give it to the person named on the balloon. "
         "Within a couple of minutes, all balloons reached the hands of the respective engineers. "
         "The manager announced this was the real solution to the problem. Many times in our life, sharing and helping others give us real solutions to problems."),
        (2019, "cloze",
         "Two months ago, when our class election started, I decided to run for class president. "
         "I enjoyed speaking in public and got along well with people, so I felt it easy to win. But I was afraid that people would feel bad for me if I lost. "
         "I was busy preparing in the following week. My plan wasn't to make promises to do things I couldn't manage but to show my class why I wanted to be president. "
         "I put up my posters in hallways and in the classroom. I also spent three hours writing my speech, saying that I was the one they could turn to whenever they had a problem. "
         "Since I was fully prepared, I felt that my chances of winning were strong. "
         "However, when I gave my speech on Election Day, the response wasn't what I had pictured. Few people actually listened. "
         "When it was my opponent's turn, everyone was screaming his name. His speech was short, but all to the point. "
         "By then, I realized I should have made mine shorter and clearer. It was obvious who would win. "
         "For the rest of the day, I felt like it was over. I wanted to just go home and cry, but I made it through. "
         "My prediction was right: I didn't win. The next day, people were still talking about the election. "
         "I just pretended not to hear. But later, things got better. People forgot about the election and talked to me just as they did before. "
         "I don't regret putting time and energy into the election because I've learned that things aren't always going the way I expect. "
         "And moments of failure like this build character, since then I've learned to face disappointment and grown stronger."),
        (2021, "cloze",
         "When Mike was seven, he knew his dream was to be a photographer. He kept working on it for years. "
         "Recently, he was trying to take a picture of a sunset to enter the school photo competition. "
         "Mom, it has been cloudy these days. I don't think I can get this picture! Mike complained. "
         "Why not use one of your photos on the computer? suggested Mom. "
         "I can't. The rules say the photos have to be taken with a traditional camera. We hand in a roll of film, it gets developed, and we choose one photo for the competition. "
         "Why is a sunset so important? Mom asked. The topic of the competition is peace, Mike explained, and I feel most peaceful seeing a sunset. "
         "Zach, his six-year-old brother, came out of the bedroom. Hey, you want to take a picture of me? Look! He put both arms over his head. "
         "Not right now, said Mike, laughing. That very afternoon, Mike felt excited when he saw clear skies. "
         "He carefully lined up his shot and waited hopefully till the sun reached the ground. That's it! Perfect! he shouted cheerfully. "
         "The next morning, Mike noticed he could take one more picture to complete the roll of film, so he walked into Zach's room. "
         "Zach was sleeping quietly with a teddy bear under his arm. Mike didn't wake Zach up, and carefully took a picture of him. "
         "A week later, Mike got the photos. The sunset picture was the one he was most eager to see. There it was! It was as nearly perfect as Mike had expected. "
         "Then, he looked through the other photos. Suddenly, he stopped. His eyebrows rose as he studied the photo of Zach. "
         "He looked back at the photo of the sunset, which seemed less perfect now. He weighed the two choices. Finally, he decided to hand in the photo of Zach for the competition."),
        (2022, "cloze",
         "I knew it was going to snow on the mountain. When we arrived, Uncle Tommie was already waiting for us. "
         "Boys, I'm not rushing you off, he said, but the wind is picking up. You'd better get the goose and head for home soon. "
         "After a quick thank-you and goodbye I took the goose and we left. Halfway up the mountain, it began to snow heavily. I held the goose close to me. "
         "By the time we reached the top of the mountain, it snowed more heavily. And the wind seemed to blow straight through my coat. "
         "I stepped in front of Rick. You must be cold. Open your coat! Are you crazy? Rick asked. I'll lose what little warmth I have! "
         "When he saw I was serious, he slowly opened his coat. I placed the warm goose inside his coat. Rick sighed happily. My plan was working. "
         "On the way down, I started to shiver. Rick said, Dave, it's your turn now. He passed me the goose. "
         "For a long moment, I just stood and warmed my freezing hands on his body. We passed the goose back and forth between us all the way. Finally, we got home. "
         "Sitting at the table, we explained how the goose kept us from freezing. We can't have him for dinner! This goose helped save our lives, I said. "
         "Later, we named the goose Charley and he lived out his life in the yard, bossing around the chickens and another goose we bought to keep him company. "
         "A life as the most important bird was fitting for our hero."),
        (2023, "cloze",
         "Where was that cashier? Impatient, I quickly looked at my watch. I hardly had enough time to eat a sandwich and rush back to work. "
         "I looked around the nearly empty restaurant, but the cashier was nowhere in sight. "
         "A woman stood wiping the far end of the counter. She looked at me coldly with sad, dark eyes. "
         "I waited, getting angry. I'd been standing there for at least three minutes! "
         "Controlling my anger, I remembered Mom's words. Whenever you find yourself in an unpleasant situation, just think about what is missing. "
         "If someone is unkind, then kindness is missing. If someone is hateful, then love is missing. "
         "If we will be what's missing, then we'll provide whatever the situation needs. "
         "And here I was in an unpleasant situation. How should I be what's missing? What was missing was service. "
         "Maybe I should just jump behind the counter and take my own order. "
         "Just then the woman walked slowly towards me. May I help you? she asked, still coldly. She looked so tired. No doubt, she was overworked. "
         "I took a deep breath. With Mom's words ringing in my head, I gave the woman my order and smiled. How are you today? "
         "My question seemed to surprise her. She eyed me for a second before answering. Not too good. "
         "I'm sorry, I said. I hope it gets better starting right now. She almost smiled as she looked at me. Thanks. I hope you're right. "
         "I thought to myself as I ate my sandwich. We're all the same, really. We have problems and angers, we get tired and we hurt. We need to be nicer to each other. "
         "After eating, I wiped the table cleaner than usual, and put the tray back nicely on the stand. "
         "The woman was watching me, a big smile on her face. Be what's missing. It worked."),
        (2024, "cloze",
         "Every summer, Serena spent two weeks at Green Farm's horseback riding camp. "
         "Last year, Serena and her favorite horse Piper finished second in the obstacle course race. "
         "I can't wait to ride Piper, Serena told Rose, her coach. Rose smiled and said, Sorry, but we need to save Piper for our newer riders this year. "
         "She's one of the best-behaved horses. How about you try riding Harley? "
         "Serena felt disappointed and was a little scared at the sight of Harley, the tallest horse, but she stayed hopeful. "
         "As she was trying to ride Harley, he went up on his back legs, throwing Serena off. She landed on the hard ground, her eyes filled with tears. "
         "I'm scared of Harley, and he's too hard to control, Serena told Rose. "
         "Harley is in a new place with a new person on his back, Rose explained. I'm sure he's pretty scared, too. But if you trust him, he will trust you. "
         "Serena decided that it was time for a fresh start. I know you're afraid of me. We're still strangers, and it's up to me to make sure that we become friends, she talked to Harley softly. "
         "After a while, Harley calmed down, and Serena realized that she was also feeling calmer. "
         "She then led Harley for a walk around the ring so that he could get used to being with her and following her directions. "
         "Soon, Serena and Harley made progress together as their confidence in each other grew. "
         "By the end of the first week, they had completed the obstacle course together. On the final day of the camp was the big race. "
         "Serena confidently climbed onto Harley. Harley, sensing the excitement of the day, ran through the course like a madman and easily won. "
         "The other horses were just no match for Harley. Rose handed Serena the winner's trophy with a wink. "
         "Serena suddenly realized that Rose had wanted her to challenge herself to be a better rider, even though she would have had a nice time with Piper. "
         "Serena gave Rose a hug and then took the trophy, and a carrot, over to Harley."),
        (2025, "cloze",
         "The New Year party was usually held at my aunt's house and my favorite part was the apple cake. "
         "At the age of 11, when I first found out that my grandfather, who was never in the kitchen, was the master behind it, I was greatly surprised. "
         "And I thought that this was the perfect chance to get the recipe, and that I could actually have a time to connect with him. "
         "Since then, I would go to my aunt's early on the morning of New Year's Day, and we'd make the cake together happily. "
         "I was amazed that Grandpa could peel an apple in one rind. And we'd mix everything and put it into the oven. "
         "Once the cake was done, the house would immediately smell like apples. But as I got older, so did Grandpa. "
         "One New Year's Day, as I was taking out the apples from the shopping bag cheerfully as usual, he looked at me and said, Sophia, what are you doing? "
         "I was shocked. I knew that he was beginning to forget things, but I didn't think he would forget this. It was our tradition. It was our time of bonding. My heart ached. "
         "We're making the apple cake. You know, we always make a cake on New Year's Day. And he said, Apple cake? Can you teach me? "
         "Now, I was terrified. Still, I guided Grandpa in making the cake because I didn't want this tradition to die. But the whole time it just didn't feel the same. "
         "Fast-forward to this New Year, Grandpa was in hospital, and we'd have our family get together there. "
         "To bring a bit of comfort to the family, I decided to make the apple cake at home by myself. But I was doubting myself the whole time. "
         "I was afraid the cake was going to taste terrible because it didn't have Grandpa's touch. "
         "At the hospital, everyone was surrounding him, creating some warmth. Grandpa looked down at the cake, and then looked back up at me and smiled. "
         "And I felt memories of our shared moments flooding back to him. Even though he was in hospital, it felt like we had made the cake together."),
        (2026, "cloze",
         "The day I walked into Westfield High School, I felt like everyone in the hallway somehow knew I was the new kid. "
         "Three weeks earlier my family moved across the country after my mum changed jobs. "
         "Starting a new school in the middle of the term felt like hitting reset on my whole life. "
         "At lunch that first day, I sat at a corner table pretending to be very interested in my phone while secretly searching for how to survive being the new kid. "
         "Teen articles kept saying the same thing: feeling worried during a school transition is normal. That helped a little, but it still felt uncomfortable. "
         "The first week was awful. I got lost looking for the chemistry class, mispronounced a teacher's name, and accidentally walked into the wrong classroom twice. "
         "But something small started to change when a boy asked if I wanted to join his group in the science lab. That made the whole day easier. "
         "One thing I learned quickly is that most students don't judge you as much as you think. Everyone is busy worrying about their own things. "
         "Slowly, I found a way to fit in. Instead of trying to do many big things right away, I focused on simple things, like learning two classmates' names a week and asking one question in a class. "
         "Those small wins slowly built up my confidence. By the end of the term, things looked very different. "
         "I joined the photography club and started hanging out with my classmates after school. "
         "Changing schools in the middle of the term was not easy, but it taught me something important about resilience and confidence. "
         "Feeling uneasy does not last forever. If you are the new kid right now, hang in there. "
         "The hallway that feels strange today may become the place where you begin your new stage of life."),
    ]
    for year, section, text in cloze:
        rows.extend(_split_passage(year, section, text))

    readings = [
        (2018, "My class were on a school field trip last week. First, we went to the University of North Carolina to learn about the history of its basketball team. "
         "Many basketball stars were students there. Then we visited a museum. We learned about how the plane was invented and took many pictures there. "
         "It was my 15th birthday last Saturday. Some of my friends and Alan, my cousin, came to celebrate it. Everyone brought me a gift. We played games, sang songs and had a big birthday cake. "
         "I was lucky enough to go to a conference on charity last Wednesday. I was so excited to meet a lot of kind people there. "
         "Last Thursday, my school band went to Atlanta to perform in a competition. I played the violin and we won a prize. "
         "On Friday we went to the Georgia Aquarium and got to see different kinds of sea life from over the world. "
         "When I was in high school, I worked part-time helping Dad sell fruits and vegetables at a market. "
         "One day, as I was preparing the fruits, a little boy came by with his mom and sister. They were looking at the fruits in front of me. "
         "Then I noticed how the mom was picking the fruits. Putting what I saw together, I was sure she was blind. "
         "Both of the kids continued to help their mom pick out the fruits. The woman then felt each one and smiled, and the daughter would put them into their basket. "
         "Their smile and gentle manner moved me in a way that never happened before. It was so beautiful to see such young kids so willingly help."),
        (2021, "When Jack was 11, he started a group to teach kids about pandas. He also sold toy pandas to raise money to protect pandas in danger. I hope to encourage more people to care about pandas, Jack says. "
         "Kathy, 14, set up an organization to educate people about growing the right plant in right places. She also wrote a book to help people learn what plants are native to their area. "
         "At the age of 12 Linda invented a machine called SuperE. It collects heat from fields to make electricity. Linda says her invention creates electricity in a way that is less harmful to the environment. "
         "Patrick, 13, joined the Ocean Heroes Camp last year. He started a project and picked up plastic waste around nearby lakes with his friends. The goal of the project was to fight plastic pollution."),
        (2021, "When I was in the eighth grade, my class was assigned to be friends with the second-grade kids. I got this little girl named Shelley. The first time I saw her, she was silent and cold. "
         "She was small for her age, and she didn't play with the other kids in her class. I tried all kinds of things to get her to talk to me. I bought her toys, crayons and candies. But try as I might, nothing worked. "
         "One Friday, I decided to tell her a story about my childhood. I told her that I felt lonely when I was with my classmates, and how I thought only my teachers liked me. "
         "Finally, when my story ended, there were tears in her eyes. And then she said, Thank you. From then on, Shelley was a different little girl. She started smiling and talking with other kids. "
         "Looking back at this I'm in awe, because all I did was to help her realize that she wasn't alone."),
        (2021, "It's not always enjoyable for children to eat vegetables. But what if a garden is built in the school? New research suggests that a gardening program in schools can increase children's vegetable intake. "
         "The study was carried out in eight schools. Every child in grades 3-5 received a total of eighteen 60-minute lessons across the school year. "
         "In the program, each school built a garden, where children learned to grow their own fresh produce, like fruit and vegetables. "
         "The study found that vegetable intake of the children who grew their own produce increased greatly across the year. "
         "Related studies show that increased vegetable intake can improve health and cut the risk of chronic diseases. "
         "Children who are often exposed to a variety of vegetables are more likely to try new foods. "
         "For children, growing their own food is a powerful tool to increase their intake of the food. "
         "Parents can listen to their children about what they have learned and read the handouts they bring home from school. "
         "Teaching children to grow their own produce is a great way to increase their preference for the produce."),
        (2021, "I remember the first time I suggested screen-free days in our school to some of our student leaders. "
         "According to a survey we did, most students in our school spend about six hours a day on screens. "
         "Many of my students start their day by checking their smartphones. They usually work on computers at school for at least two hours during the day. "
         "It's clear that our students spend a lot of time on screens. We do see the benefits of technology. "
         "However, we teachers also want to make sure that students have balanced learning and social experiences away from their screens. "
         "Fun activities, for example, card games and room escape games, are organized at school. "
         "In these activities, students socialize without smartphones and have face-to-face communication. "
         "After our first screen-free day, students mentioned that they were surprised they enjoyed it. "
         "While technology is already part of our world, it shouldn't play such an important role in a learner's life."),
        (2024, "White's is a place for fruit lovers. In this store, you'll find different kinds of fruits. They are all grown on our local farms and sold at low prices. "
         "William's is in a beautiful new building. The store sells fresh food. It also makes tasty cakes and cookies to take away, great for celebrations. "
         "This store offers women's clothes. Many of them are made from natural materials. There's also an area selling beautiful handmade hats. "
         "This store is popular for its shoes at fair prices. And it is always the first in town to offer children's clothing in new designs. "
         "Mother's Day is coming. I'd like to buy a beautiful hat for my mom. I'm sure she will like it. "
         "Mary and I will hold a birthday party for our friend, Lucy. So, I need to buy a big cake and some cookies for the party. "
         "My grandpa likes doing morning exercise in the park. I want to buy him a pair of sports shoes as a gift."),
        (2024, "The school year began. As president of the recycling club, Scott was thinking about new activities to encourage other students to become more enthusiastic about recycling. "
         "His club had helped to recycle a lot of waste for the past five years and he hoped that this year they would do even better. "
         "During his research, he learned that the amount of electronic waste, or e-waste, is increasing rapidly. "
         "There is a special project I want us to work on this term, Scott announced at the recycling club meeting the next day. "
         "We have all heard about e-waste, but recently I learned about the bad effects it's having on our environment. "
         "He wanted them to organize an e-waste drive, a day when students and their families could drop off unwanted electronics to be recycled. "
         "The big day finally arrived, and Scott was nervous. Phones, TV sets, computers and keyboards soon began piling up. "
         "Scott smiled, realizing that a simple action could truly have a lasting influence."),
        (2024, "Sam Hill is really bad at finding his way from place to place. "
         "Researchers developed an online game in which players travel by boat to find where a lot of checkpoints lie. "
         "The game asked players to provide basic background information, and nearly four million people worldwide did so. "
         "The researchers found that Northern Europeans seemed to be better navigators, perhaps because they love orienteering, a sport which involves cross-country running and navigation. "
         "And those from cities with more disorganized street networks did better than those from cities with orderly ones. "
         "Research results like these suggest that people's life experience decides how well they find their way. "
         "It turns out that this difference is more a question of culture and experience than of inborn ability."),
        (2024, "Recently, I started to use an app to keep a record of my running. Each run I wanted to go a little farther, run a little faster and burn more calories. "
         "This inner self-comparison left me feeling disappointed. I became so focused on the numbers that I forgot to consider what I achieved. "
         "We should exercise for the purpose of building our confidence. Fitness should help us with our quality of life, the ability to sleep, good memory, among other things. "
         "Fitness should not just come with the eagerness for the success in numbers. "
         "When we do physical exercise, we should value what feels good over what looks or sounds good. "
         "Apps of this kind are a great way for us to keep an eye on our health. "
         "So my advice is: when you do physical exercise, make sure you feel good about yourself over feeling good about the numbers."),
        (2025, "I want to travel to Africa and see the animals. I'd love to take lots of photos of elephants, giraffes and other animals. I'd like to try sleeping in a tent in the wild. "
         "I'd like to go to North America. I love to walk in forests, climb trees and hike in the mountains. Perhaps I could go birdwatching, too. I enjoy exploring nature. "
         "I've decided to tour Australia with my family. My plan is to go to the beach, swim in the sea and sit in the sun. Also, we're going to play volleyball on the beach."),
        (2025, "When I was young, flowers filled my mom's garden each spring. One day last November, Mom and I spent a whole morning planting flower bulbs. "
         "I dropped one in each hole and covered it over with soil. Then Mom told me to wait. I watched hopefully all through the winter. "
         "On the last day of April, I went outside to find the garden full of colorful flowers. Our hard work paid off. "
         "My boy, tomorrow morning, Mom said, we will walk the neighborhood and leave a basket of flowers on each doorstep. "
         "Flowers are like kindness, Mom said. Their beauty is meant to be shared. "
         "I took one basket, set it by the doorstep and rang the bell. A man came out, looking surprised. He picked up the flower basket and then smiled. "
         "The garden was empty, but my heart was full."),
        (2025, "Imagine a robot. What comes to your mind first? A machine stronger than the human body? "
         "However, this same quality is now causing a big problem. It's creating tons of long-lasting e-waste that could flood our planet. "
         "Researchers made a robotic arm and a controller using materials from animals and plants. These materials are strong enough to work but can easily break down in a natural environment. "
         "After testing, both parts were gone in soil within weeks. Biodegradable robotics often falls under the umbrella of soft robotics, which takes ideas from nature. "
         "Wei and Zhang expect that robots like these can be used to deal with dangerous waste and then disappear naturally. "
         "They also hope that such robots can aid doctors in operations and then safely break down inside the body."),
        (2025, "People are talking a lot about artificial intelligence, viewing it as a force that could reshape how society works. "
         "Every AI model we develop mirrors our rules and expresses our beliefs. "
         "A few years ago, while looking for new workers, a famous company gave up an AI-powered tool after finding it unfavorable to women. "
         "The AI was not designed to behave this way; instead, it was influenced by the historical data favoring men. "
         "In both cases, AI isn't creating new biases, it is mirroring the ones that are already present. "
         "As long as AI is trained on human data, it will reflect human behavior. That means we have to think carefully about the footprints of ourselves we leave in the world."),
        (2025, "We do everything in a hurry, finishing our meals, completing our tasks, running to the gyms. We choose fast living because we think we have no control of time. "
         "The Slow Movement thinks that the answer to our predicament is not to live faster, but to learn how to live slower. "
         "The movement began with the Slow Food Program, which was set up in 1986. It believed that we should fight against fast-food restaurants, protect traditional cooking, and encourage people to enjoy preparing and eating food. "
         "The main idea of the Slow Movement is to value quality over quantity. Slow living is a lifestyle based on the Slow Movement. "
         "Its goal is to free us from endless rush that stops us from enjoying moments of rest."),
        (2026, "Do you want to ride a horse? Welcome to try it in our park. All our horses are carefully chosen and well trained. They are safe to ride, even for beginners. "
         "Are you a fan of biking? Join us and bike around the lake. Just follow the flat paths and you will be greeted by beautiful flowers and trees. "
         "You can have a happy time outdoors and make new friends. Welcome to our family-friendly garden in the city centre. We have many kinds of flowers. "
         "You can learn about their names and the places they come from. By the way, you will find many snack shops at the south gate. "
         "Hope to ride a 50-year-old train? Get on the train for a relaxing two-hour trip around the city. You can have a great time while enjoying the beautiful view along the way."),
        (2026, "Linda always dreamed of having many great toys, but buying them all was almost impossible. "
         "One afternoon, exploring behind her apartment building, Linda discovered something wonderful. An elderly woman was creating beautiful playthings using thrown-away materials and natural objects. "
         "How do you make such wonderful toys without buying anything? Linda asked, amazed. "
         "The best toys aren't bought in stores, the woman smiled warmly. They're created with your own hands and imagination. "
         "Inspired, Linda began trying out some ideas at home. A shoe box became a tiny theatre. Old socks turned into materials for fashion dolls and old magazines became their clothes. "
         "What if we have a toy-making workshop where students can make their own toys for show-and-tell? "
         "The handmade toys fired everyone's imagination in ways store toys never could. "
         "She realised creativity can also be about finding possibilities in seemingly useless materials."),
        (2026, "While the size of Arctic sea ice has dropped by about 40 percent over 40 years, until recently, the size of the sea ice around Antarctica was slowly increasing. "
         "Then, after 2015, Antarctic ice extent fell from a record high to several record lows, losing an area as large as Greenland. "
         "Some research has suggested that higher air temperatures may be the cause. However, two new studies show that ocean warming played a bigger role in this dramatic change. "
         "As part of global ocean circulation, warm saltwater moves southward from the tropics and circles Antarctica 200 metres below the surface. "
         "The researchers plan to study and model other things, which also likely play roles throughout Antarctica."),
        (2026, "The internet has provided us with unmatched ways to get information, but it is also sounding alarms. "
         "Some experts argue that the internet will produce forgetfulness in the minds of those learning to use it, because they won't practise their memory. "
         "But our brains don't work well when we're not focused. When we repeatedly check text messages and social media during work, we are weakening our ability to form both short-and long-term memories. "
         "Trying to actively recall data is a good workout for the brain, but today we are using online search tools instead. "
         "However, the internet may be changing only what we remember, not our ability to do so. "
         "There may be costs caused by our increased dependence on the internet, but generally the benefits are going to outweigh those costs."),
        (2026, "Being busy often seems important in today's world. Full calendars, nonstop notifications, and long to-do lists make it feel like progress is always happening. "
         "However, many people end their days very tired and wonder why their big goals are still far away. "
         "The truth is that being busy is different from being effective: one fills time and the other creates results. "
         "Understanding the difference is important because it helps you control your attention, make smarter choices, and focus on what truly matters. "
         "Effectiveness, however, is measured by results, not activity. Rather than ask how much was done, effective people ask what was achieved. "
         "They prioritise tasks that create meaningful change, even if those tasks require more focus and more effort."),
    ]
    for year, text in readings:
        rows.extend(_split_passage(year, "reading", text))

    _load_extra(rows)

    # 去重（同地同年同句）
    seen = set()
    uniq: List[dict] = []
    for r in rows:
        k = (r.get("place") or "北京", r["year"], r["en"].lower())
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


def _load_extra(rows: List[dict]) -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    zh = _zh_map()
    for name in ("beijing_zhongkao_extra.json", "zhongkao_national_extra.json"):
        path = data_dir / name
        if not path.exists():
            continue
        extra = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(extra, list):
            continue
        for item in extra:
            if not isinstance(item, dict):
                continue
            try:
                year = int(item.get("year") or 0)
            except (TypeError, ValueError):
                continue
            section = str(item.get("section") or "grammar")
            place = str(item.get("place") or "北京")
            en = str(item.get("en") or "")
            cn = str(item.get("cn") or "")
            if not en.strip():
                continue
            if item.get("split"):
                rows.extend(_split_passage(year, section, en, zh, place=place))
            else:
                _add(rows, year, section, en, cn, place=place)


@lru_cache(maxsize=1)
def _zh_map() -> Dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "data" / "beijing_zhongkao_zh.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, str] = {}
    for k, v in raw.items():
        key = (k or "").strip()
        val = (v or "").strip()
        if key and val:
            out[key] = val
            out[key.lower()] = val
    return out


def _apply_zh(rows: List[dict]) -> List[dict]:
    mapping = _zh_map()
    if not mapping:
        return rows
    for r in rows:
        if (r.get("cn") or "").strip():
            continue
        en = (r.get("en") or "").strip()
        r["cn"] = mapping.get(en) or mapping.get(en.lower()) or ""
    return rows


CORPUS: List[dict] = _apply_zh(_build())
