def weather_icon(code):

    if code==0:
        return "☀️"

    elif code in [1,2]:
        return "🌤"

    elif code==3:
        return "☁️"

    elif code in [45,48]:
        return "🌫"

    elif code in [51,53,55]:
        return "🌦"

    elif code in [61,63,65]:
        return "🌧"

    elif code in [71,73,75]:
        return "❄️"

    elif code in [95,96,99]:
        return "⛈"

    return "❓"