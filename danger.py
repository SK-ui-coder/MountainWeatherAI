def judge(wind, rain):
    score = 100

    if wind >= 20:
        score -= 60
    elif wind >= 15:
        score -= 40
    elif wind >= 10:
        score -= 20

    if rain >= 80:
        score -= 40
    elif rain >= 50:
        score -= 20
    elif rain >= 30:
        score -= 10

    if score >= 90:
        return "🟢 安全", score
    elif score >= 70:
        return "🟡 注意", score
    elif score >= 50:
        return "🟠 危険", score
    else:
        return "🔴 登山中止推奨", score
    
def recommend(score):

    if score >= 90:
        return "★★★★★"

    elif score >= 80:
        return "★★★★☆"

    elif score >= 70:
        return "★★★☆☆"

    elif score >= 60:
        return "★★☆☆☆"

    else:
        return "★☆☆☆☆"    