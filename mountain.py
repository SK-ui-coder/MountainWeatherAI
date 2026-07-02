def summit_temp(base_temp, height):
    """
    標高による気温補正
    100m上がるごとに約0.65℃低下
    """

    summit = base_temp - (height * 0.0065)

    return round(summit, 1)
