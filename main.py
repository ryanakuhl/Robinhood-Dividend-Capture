"""
How it works:
    1. logs into Robinhood
    2. Go to dividata.com and find a list of good dividend stocks that  are about to payout
    3. Sells stocks that have already paid and you have profited from
    4. Buys new stocks based off the dividata list, then tries again in case the sell limit wasn't reached the first time
"""

"""

Needs :
        your Robinhood email address on line 45
        your free https://iextrading.com/developer/ api token on line 90

"""

"""
Headaches:
    1. Without "store_session=False" (line 45), you have to delete the pickle file everyday.
       Without "store_session=False" (line 45), you have to enter your verification every login.
    2. Buy/sell parameters may need adjusting
    3. Your RH encrypted password is saved as grocery_list.txt. I guess a vulnerability.
    3. There's a GUI for sell but not buy because YOU GOTTA WARN PEOPLE!!!!
"""

import robin_stocks as r
from datetime import datetime
from bs4 import BeautifulSoup
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import xlrd, requests, json, time, base64, warnings, easygui
from currency_converter import CurrencyConverter

c = CurrencyConverter()
today = datetime.now()
tomorrow = []

try:
    with open('grocery_list.txt') as f:
        lettuce = base64.b64decode(f.read())
except FileNotFoundError:
    with open('grocery_list.txt', 'w') as f:
        lettuce = base64.b64encode(
            bytes(easygui.passwordbox(msg='Let me have that', title='Please'), 'utf-8'))
        f.write("".join(chr(x) for x in lettuce))
login = r.login('**************@gmail.com', lettuce)#, store_session=False)

class AnalyzeStock:
    def __init__(self, x):
            self.Symbol = x[0]
            self.Name = x[1]
            try:
                self.Last_Close = float(x[2].replace('$', ''))
            except:
                self.Last_Close = 1000
            self.Dividend_Yield = x[3].replace('%', '')
            self.Years_Paying = x[4]
            self.Dividata_Rating = x[5]
            self.Payout_Date = ''
            self.Payout_Amount = 0
            self.Payout_Ratio = 0
            self.Payout_Per_Day = 0
            self.ask_price = 1000
            self.bid_price = 1000
            self.last_trade_price = 1000

def dividend_filter(stocks):
    my_list = []
    for stock in stocks:
        if 'N/A' not in stock.Dividata_Rating:
            if int(stock.Dividata_Rating) >= 4:
                my_list.append(stock)
    return my_list

def years_paid_filter(good_div):
    my_list = []
    for stock in good_div:
        if int(stock.Years_Paying) >= 7:
            my_list.append(stock)
    return my_list

def yield_filter(good_years):
    my_list = []
    for stock in good_years:
        if float(stock.Dividend_Yield) >= 4:
            my_list.append(stock)
    return my_list

def funt_stock_basic(g):
    warnings.simplefilter('ignore', InsecureRequestWarning)
    p = requests.get('https://cloud.iexapis.com/stable/stock/' + g.Symbol + '/dividends?token=********your token*******', verify=False)
    p = json.loads(p.content.decode('utf-8'))[0]
    g.Payout_Amount = round(c.convert(p.get('amount'), p.get('currency'), 'USD'), 2)
    g.Payout_Date = p.get('recordDate')
    g.Payout_Ratio = g.Payout_Amount / g.Last_Close
    g.Payout_Per_Day = round(((g.Payout_Ratio / (datetime.strptime(g.Payout_Date, '%Y-%m-%d') - today).days)*100), 4)

def sell_old_stocks():
    divies = [[x.get('instrument'), x.get('record_date')] for x in r.get_dividends()]
    positions_data = r.get_current_positions()
    for position in positions_data:
        for d in divies:
            if position.get('instrument') in d[0]:
                about = r.request_get(position['instrument'])
                div_diff = (datetime.strptime(d[1], '%Y-%m-%d') - today).days
                if div_diff <= 0:
                    stock_dict = r.stocks.get_stock_quote_by_symbol(about.get('symbol'))
                    last_trade_price = float(stock_dict.get('last_trade_price'))
                    if last_trade_price / float(position['average_buy_price']) > 1.005:
                        if float(position.get('shares_held_for_sells')) == 0:
                            if easygui.ccbox(msg=about.get('symbol') + '\n' + d[1] + '\nQuantity: ' + str(position['quantity']) + '\nPurchase $' + str(float(position['average_buy_price'])) + '\nCurrent price $' + str(last_trade_price) + '\nProfit per $' + str(float(last_trade_price) - float(position['average_buy_price'])) + '\nTotal win $' + str((float(last_trade_price) - float(position['average_buy_price']))*float(position['quantity'])) + '\nROI ' + str(100 - (float(last_trade_price) / float(position['average_buy_price']))*-100) + '%'  ):
                                r.order_sell_limit(about.get('symbol'), position['quantity'], round(last_trade_price*1.0035, 2))
                                print('selling ', about.get('symbol'))
                else:
                    stock_dict = r.stocks.get_stock_quote_by_symbol(about.get('symbol'))
                    last_trade_price = float(stock_dict.get('last_trade_price'))
                    if last_trade_price / float(position['average_buy_price']) > 1.015:
                        if float(position.get('shares_held_for_sells')) == 0:
                            if easygui.ccbox(msg='NO DIVVIE SALE\n' +about.get('symbol') + '\n' + d[1] + '\nQuantity: ' + str(position['quantity']) + '\nPurchase $' + str(float(position['average_buy_price'])) + '\nCurrent price $' + str(last_trade_price) + '\nProfit per $' + str(float(last_trade_price) - float(position['average_buy_price'])) + '\nTotal win $' + str((float(last_trade_price) - float(position['average_buy_price'])) * float(position['quantity'])) + '\nROI ' + str(100 - (float(last_trade_price) / float(position['average_buy_price'])) * -100) + '%'):
                                r.order_sell_limit(about.get('symbol'), position['quantity'], round(last_trade_price * 1.0035, 2))
                                print('selling ', about.get('symbol'))

def targeting_stocks(table):
    rows = table.find_all('tr')
    stocks = [AnalyzeStock([td.text for td in row.find_all('td')]) for row in rows]
    good_div = dividend_filter(stocks)
    good_years = years_paid_filter(good_div)
    good_yield = yield_filter(good_years)
    for g in good_yield:
        if r.stocks.get_stock_quote_by_symbol(g.Symbol):
            try:
                stock_dict = r.stocks.get_stock_quote_by_symbol(g.Symbol)
                g.ask_price = float(stock_dict.get('ask_price'))
                g.bid_price = float(stock_dict.get('bid_price'))
                g.last_trade_price = float(stock_dict.get('last_trade_price'))
                previous_close = stock_dict.get('previous_close')
                funt_stock_basic(g)
                time.sleep(2)
            except Exception as e:
                good_yield.remove(g)

    return sorted(good_yield, key=lambda x: x.Payout_Per_Day, reverse=True)

def target_stocks():
    page = requests.get('https://dividata.com/dividates')
    soup = BeautifulSoup(page.content, 'html.parser')
    tables = soup.find_all('tbody')
    global tomorrow
    tomorrow = targeting_stocks(tables[1])
    return targeting_stocks(tables[0])

def get_new_stocks():
    play_money = float(r.load_account_profile()['margin_balances'].get('day_trade_buying_power'))
    current_holdings = r.build_holdings().keys()
    for g in g_sorted[:1]:
        if g.Symbol in current_holdings:
            pass
        else:
            shares_to_buy = round(play_money/g.last_trade_price)
            if shares_to_buy > 0:
                r.orders.order_buy_limit(g.Symbol, int(shares_to_buy), round(float(g.last_trade_price*.995), 2), timeInForce='gfd')
                play_money = play_money - (shares_to_buy * g.last_trade_price)
                print('placed for today ', g.Name)

    for g in tomorrow[:1]:
        if g.Symbol in current_holdings:
            pass
        else:
            shares_to_buy = round(play_money / g.last_trade_price)
            if shares_to_buy > 0:
                r.orders.order_buy_limit(g.Symbol, int(shares_to_buy), round(float(g.last_trade_price * .985), 2), timeInForce='gfd')
                play_money = play_money - (shares_to_buy * g.last_trade_price)
                print('placed for tomorrow ', g.Name)

    for g in g_sorted[1:2]:
        if g.Symbol in current_holdings:
            pass
        else:
            shares_to_buy = round(play_money/g.last_trade_price)
            if shares_to_buy > 0:
                r.orders.order_buy_limit(g.Symbol, int(shares_to_buy), round(float(g.last_trade_price * .995), 2),  timeInForce='gfd')
                print('Runner up today ', g.Name)

    for g in tomorrow[1:2]:
        if g.Symbol in current_holdings:
            pass
        else:
            shares_to_buy = round(play_money/g.last_trade_price)
            if shares_to_buy > 0:
                r.orders.order_buy_limit(g.Symbol, int(shares_to_buy), round(float(g.last_trade_price * .98), 2),  timeInForce='gfd')
                print('Runner up tomorrow ', g.Name)

g_sorted = target_stocks()
sell_old_stocks()
time.sleep(60*1)
get_new_stocks()
time.sleep(60*3)
get_new_stocks()
