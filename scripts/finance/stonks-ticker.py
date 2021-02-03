from yahoofinancials import YahooFinancials
from servertools import SlackComm

stonk = '6098.T'

yf = YahooFinancials(stonk)

price = yf.get_current_price()
change = yf.get_current_change()
pct_change = yf.get_current_percent_change()

scom = SlackComm('viktor')

jpyusd = 1/104.48
units = 1000
strike_price = 4542
msg = f'{units:,.0f} shares is now worth *`{(price - strike_price) * jpyusd * units:+,.0f}`* USD' \
      f' more than when you got it'

blocks = [
    scom.bkb.make_context_section(f':trending_up_and_down: time for stonk updates !'),
    scom.bkb.make_block_section(msg),
    scom.bkb.make_context_section([
        f'JPY/USD: {jpyusd:.4f}, strike price: {strike_price}, current price: {price}'
    ])
]

scom.st.send_message('C01M49M5EEM', message='stonk update', blocks=blocks)
