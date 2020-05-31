from servertools import RokuTV


rktv = RokuTV()
rktv.power()

app = rktv.get_app_by_name('prime video')
app.launch()

