def equipment(temp,wind,rain):

    items=[]

    items.append("🥾 登山靴")

    if temp<=10:
        items.append("🧥 防寒着")

    if rain>=30:
        items.append("☔ レインウェア")

    if wind>=10:
        items.append("🧤 手袋")

    if wind>=15:
        items.append("🥽 ゴーグル")

    if temp<=5:
        items.append("🧢 ニット帽")

    return items