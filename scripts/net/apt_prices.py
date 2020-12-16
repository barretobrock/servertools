import re
import pandas as pd
from servertools import BrowserAction
from kavalkilu import LogWithInflux, InfluxDBLocal, InfluxDBTracker


logg = LogWithInflux('apt-prices', log_to_file=False)
influx = InfluxDBLocal(InfluxDBTracker.APT_PRICES)
ba = BrowserAction(headless=True, parent_log=logg)
url = 'https://www.maac.com/available-apartments/?propertyId=611831&Bedroom=2%20Bed'

ba.get(url)

ba.medium_wait()
listings = ba.get_elem('//div[contains(@class, "apartment-listing")]/div[contains(@class, "apartment")]',
                       single=False)
logg.debug(f'Returned {len(listings)} initial listings...')
apt_list = []
for apt in listings:
    apt_dict = {}
    # Get unit
    unit = apt.find_element_by_xpath('.//div[contains(@class, "apartment__unit-number")]').text
    # Clean unit of non-number chars
    unit = re.search(r'\d+', unit).group()
    # Get sqft, beds, baths
    desc = apt.find_element_by_xpath('.//div[contains(@class, "apartment__unit-description")]').text.split('\n')
    for d in desc:
        for item in ['bed', 'bath', 'sq. ft.']:
            if item in d.lower():
                apt_dict[re.sub(r'\W+', '', item)] = int(re.search(r'\d+', d).group())
                break
    # Get price
    price = apt.find_element_by_xpath('.//div[contains(@class, "apartment__price")]'
                                      '/div[contains(@class, "apartment__description")]').text
    price = int(''.join(re.findall(r'\d+', price)))
    apt_dict.update({
        'price': price,
        'unit': unit
    })
    apt_list.append(apt_dict)

ba.tear_down()
logg.debug(f'Processed {len(apt_list)} listings...')

if len(apt_list) > 0:
    # Add to influx
    apt_df = pd.DataFrame(apt_list)
    logg.debug(f'Writing {apt_df.shape[0]} rows to influx...')
    influx.write_df_to_table(apt_df, tags='unit', value_cols=['bed', 'bath', 'sqft', 'price'])

logg.close()
