from yahoofinancials import YahooFinancials
from servertools import SlackComm

stonk = '6098.T'

yf = YahooFinancials(stonk)

price = yf.get_current_price()
change = yf.get_current_change()
pct_change = yf.get_current_percent_change()
prev_close = yf.get_prev_close_price()
ann_high = yf.get_yearly_high()
ma50d = yf.get_50day_moving_avg()
ma200d = yf.get_200day_moving_avg()

scom = SlackComm('viktor')

jpyusd = 1/104.48
units = 100
strike_price = 4542
msg = f'{units:,.0f} shares of `{stonk}` are now worth *`{(price - strike_price) * jpyusd * units:+,.2f}`* USD' \
      f' more than when you got it'


def format_value(val: float) -> str:
    emoji = 'poo-money' if val > 0 else 'poo-blood-money'
    return f':{emoji}: *`{val:+.2%}`*'


blocks = [
    scom.bkb.make_context_section(f':trending_up_and_down: time for stonk updates !'),
    scom.bkb.make_block_section(msg),
    scom.bkb.make_block_section(f'''
    *Facts:*
        {format_value((price - prev_close) / prev_close)} chg from previous closing price (`{prev_close:.0f}` JPY)
        {format_value((price - ma50d) / ma50d)} from 50d MA (`{ma50d:.0f}` JPY)
        {format_value((price - ma200d) / ma200d)} from 200d MA (`{ma200d:.0f}` JPY)
        {format_value((price - ann_high) / ann_high)} from annual high (`{ann_high:.0f}` JPY)
        {format_value((price - strike_price) / strike_price)} from strike
    '''),
    scom.bkb.make_context_section([
        f'JPY/USD: {jpyusd:.4f}, strike price: {strike_price} JPY, current price: {price} JPY'
    ])
]

scom.st.send_message('C01M49M5EEM', message='stonk update', blocks=blocks)
