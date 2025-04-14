from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests

class VexMeliCampaignPADS(models.Model):
    _name               = "vex.meli.campaign.pads"
    _description        = "Model for PADS meli advertiser's campaigns"

    @api.model
    def get_latest_campaigns(self, option):
        today = datetime.today().date()
        if option == "7":
            date_ago = today - relativedelta(days=7)
        elif option == "15":
            date_ago = today - relativedelta(days=15)
        elif option == "30":
            date_ago = today - relativedelta(days=30)
        elif option == "60":
            date_ago = today - relativedelta(days=60)
        elif option == "90":
            date_ago = today - relativedelta(days=90)

        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        
        ACCESS_TOKEN = meli_instance.access_token
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}",
                   "api-version": "2"}
        url_advertiser = f"https://api.mercadolibre.com/advertising/advertisers?product_id=PADS"
        res_advertiser = requests.get(url_advertiser, headers=headers)
        data_response_advertiser = res_advertiser.json()
        if res_advertiser.status_code == 200:
            advertiser_id = data_response_advertiser['advertisers'][0]['advertiser_id']
            url_campaigns = "https://api.mercadolibre.com/advertising/advertisers/{0}/product_ads/campaigns?offset=0&date_from={1}&date_to={2}&metrics=clicks,prints,ctr,cost,cpc,acos,organic_units_quantity,organic_units_amount,organic_items_quantity,direct_items_quantity,indirect_items_quantity,advertising_items_quantity,cvr,roas,sov,direct_units_quantity,indirect_units_quantity,units_quantity,direct_amount,indirect_amount,total_amount".format(advertiser_id, date_ago, today)
            res_campaigns = requests.get(url_campaigns, headers=headers)
            data_response_campaigns = res_campaigns.json()
            result = []
            def format_currency(value):
                return "${:,.2f}".format(value)
            if res_campaigns.status_code == 200:
                for rec in data_response_campaigns['results']:
                    name_camp = rec.get('name')
                    if len(name_camp) > 20:
                        name_camp = name_camp[:20] + "..."
                    result.append({
                        'id': rec.get('id'),
                        'name': name_camp,
                        'status': rec.get('status'),
                        'strategy': rec.get('strategy'),
                        'budget': format_currency(rec.get('budget')),
                        'acos_target': rec.get('acos_target'),
                        'advertising_items_quantity': rec.get('metrics').get('advertising_items_quantity'),
                        'prints': rec.get('metrics').get('prints'),
                        'clicks': rec.get('metrics').get('clicks'),
                        'total_amount': format_currency(rec.get('metrics').get('total_amount')),
                        'cost': format_currency(rec.get('metrics').get('cost')),
                        'acos': rec.get('metrics').get('acos')
                    })
                return result 
            elif res_campaigns.status_code == 401:
                print(f"Error {res_campaigns.status_code}: {res_campaigns.text}")
                raise UserError(f"Error getting data from API: {data_response_campaigns['message']}, refresh access token to continue")     
            else:
                print(f"Error {res_campaigns.status_code}: {res_campaigns.text}")
                raise UserError(f"Error getting data from API: {data_response_campaigns['message']}")              
        elif res_advertiser.status_code == 401:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}, refresh access token to continue")
        else:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}")

    @api.model
    def get_latest_advertisement(self, camp_id, option):
        today = datetime.today().date()
        if option == "7":
            date_ago = today - relativedelta(days=7)
        elif option == "15":
            date_ago = today - relativedelta(days=15)
        elif option == "30":
            date_ago = today - relativedelta(days=30)
        elif option == "60":
            date_ago = today - relativedelta(days=60)
        elif option == "90":
            date_ago = today - relativedelta(days=90)

        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id

        ACCESS_TOKEN = meli_instance.access_token
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}",
                   "api-version": "2"}
        url_advertiser = f"https://api.mercadolibre.com/advertising/advertisers?product_id=PADS"
        res_advertiser = requests.get(url_advertiser, headers=headers)
        data_response_advertiser = res_advertiser.json()
        if res_advertiser.status_code == 200:
            advertiser_id = data_response_advertiser['advertisers'][0]['advertiser_id']
            url_advertisements = "https://api.mercadolibre.com/advertising/advertisers/{0}/product_ads/items?date_from={1}&date_to={2}&metrics=clicks,prints,ctr,cost,cpc,acos,organic_units_quantity,organic_units_amount,organic_items_quantity,direct_items_quantity,indirect_items_quantity,advertising_items_quantity,cvr,roas,sov,direct_units_quantity,indirect_units_quantity,units_quantity,direct_amount,indirect_amount,total_amount&limit=115&filters[campaign_id]={3}".format(advertiser_id, date_ago, today, camp_id)
            res_advertisements = requests.get(url_advertisements, headers=headers)
            data_response_advertisements = res_advertisements.json()
            print(data_response_advertisements)
            result = []
            def format_currency(value):
                return "${:,.2f}".format(value)
            if res_advertisements.status_code == 200:
                for rec in data_response_advertisements['results']:
                    title = rec.get('title')
                    if len(title) > 20:
                        title = title[:20] + "..."
                    result.append({
                        'id': rec.get('id'),
                        'campaign_id': rec.get('campaign_id'),
                        'product': rec.get('user_product_id') if rec.get('user_product_id') != None else "",
                        'status': rec.get('status'),
                        'title': title,
                        'prints': rec.get('metrics').get('prints'),
                        'clicks': rec.get('metrics').get('clicks'),
                        'cpc': format_currency(rec.get('metrics').get('cpc')),
                        'advertising_items_quantity': rec.get('metrics').get('advertising_items_quantity'),
                        'total_amount': format_currency(rec.get('metrics').get('total_amount')),
                        'cost': format_currency(rec.get('metrics').get('cost')),
                        'acos': rec.get('metrics').get('acos')
                    })
                return result  
            elif res_advertisements.status_code == 401:
                print(f"Error {res_advertisements.status_code}: {res_advertisements.text}")
                raise UserError(f"Error getting data from API: {data_response_advertisements['message']}, refresh access token to continue")   
            else:
                print(f"Error {res_advertisements.status_code}: {res_advertisements.text}")
                raise UserError(f"Error getting data from API: {data_response_advertisements['message']}")               
        elif res_advertiser.status_code == 401:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}, refresh access token to continue")
        else:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}") 

class VexMeliBADS(models.Model):
    _name               = "vex.meli.bads"
    _description        = "Model for BADS meli advertiser's campaigns"

    @api.model
    def get_latest_campaigns(self, option):
        today = datetime.today().date()
        if option == "7":
            date_ago = today - relativedelta(days=7)
        elif option == "15":
            date_ago = today - relativedelta(days=15)
        elif option == "30":
            date_ago = today - relativedelta(days=30)
        elif option == "60":
            date_ago = today - relativedelta(days=60)
        elif option == "90":
            date_ago = today - relativedelta(days=90)

        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id

        ACCESS_TOKEN = meli_instance.access_token
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}",
                   "api-version": "2"}
        url_advertiser = f"https://api.mercadolibre.com/advertising/advertisers?product_id=BADS"
        res_advertiser = requests.get(url_advertiser, headers=headers)
        data_response_advertiser = res_advertiser.json()
        if res_advertiser.status_code == 200:
            advertiser_id = data_response_advertiser['advertisers'][0]['advertiser_id']
            url_campaigns = "https://api.mercadolibre.com/advertising/advertisers/{0}/brand_ads/campaigns".format(advertiser_id)
            res_campaigns = requests.get(url_campaigns, headers=headers)
            data_response_campaigns = res_campaigns.json()
            result = []
            if res_campaigns.status_code == 200:
                for camp in data_response_campaigns['campaigns']:
                    campaign_id = camp.get('campaign_id')
                    url_campaigns_metrics = "https://api.mercadolibre.com/advertising/advertisers/{0}/brand_ads/campaigns/{1}/metrics?limit=100&offset=0&date_from={2}&date_to={3}".format(advertiser_id, campaign_id, date_ago, today)
                    res_campaigns_metrics = requests.get(url_campaigns_metrics, headers=headers)
                    data_response_campaigns_metrics = res_campaigns_metrics.json()
                    if res_campaigns_metrics.status_code == 200:
                        def format_currency(value):
                            return "${:,.2f}".format(value)
                        name_camp = camp.get('name')
                        if len(name_camp) > 20:
                            name_camp = name_camp[:20] + "..."
                        result.append({
                            'id': camp.get('campaign_id'),
                            'name': name_camp,
                            'status': camp.get('status'),
                            'type': camp.get('campaign_type'),
                            'start_date': camp.get('start_date').split("T")[0],
                            'end_date': camp.get('end_date').split("T")[0],
                            'budget': format_currency(camp.get('budget').get('amount')),
                            'units_quantity': data_response_campaigns_metrics.get('summary').get('event_time').get('units_quantity'),
                            'clicks': data_response_campaigns_metrics.get('summary').get('clicks'),
                            'units_amount': data_response_campaigns_metrics.get('summary').get('event_time').get('units_amount'), 
                            'consumed_budget': format_currency(data_response_campaigns_metrics.get('summary').get('consumed_budget')), 
                            'acos': data_response_campaigns_metrics.get('summary').get('acos')
                        })
                    elif res_campaigns_metrics.status_code == 401:
                        print(f"Error {res_campaigns_metrics.status_code}: {res_campaigns_metrics.text}")
                        raise UserError(f"Error getting data from API: {data_response_campaigns_metrics['message']}, refresh access token to continue")     
                    else:
                        print(f"Error {res_campaigns_metrics.status_code}: {res_campaigns_metrics.text}")
                        raise UserError(f"Error getting data from API: {data_response_campaigns_metrics['message']}")
                return result 
            elif res_campaigns.status_code == 401:
                print(f"Error {res_campaigns.status_code}: {res_campaigns.text}")
                raise UserError(f"Error getting data from API: {data_response_campaigns['message']}, refresh access token to continue")     
            else:
                print(f"Error {res_campaigns.status_code}: {res_campaigns.text}")
                raise UserError(f"Error getting data from API: {data_response_campaigns['code']}")              
        elif res_advertiser.status_code == 401:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}, refresh access token to continue")
        else:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}")
    
    @api.model
    def get_latest_keywords(self, camp_id, option):
        today = datetime.today().date()
        if option == "7":
            date_ago = today - relativedelta(days=7)
        elif option == "15":
            date_ago = today - relativedelta(days=15)
        elif option == "30":
            date_ago = today - relativedelta(days=30)
        elif option == "60":
            date_ago = today - relativedelta(days=60)
        elif option == "90":
            date_ago = today - relativedelta(days=90)

        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id

        ACCESS_TOKEN = meli_instance.access_token
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}",
                   "api-version": "2"}
        url_advertiser = f"https://api.mercadolibre.com/advertising/advertisers?product_id=BADS"
        res_advertiser = requests.get(url_advertiser, headers=headers)
        data_response_advertiser = res_advertiser.json()
        if res_advertiser.status_code == 200:
            advertiser_id = data_response_advertiser['advertisers'][0]['advertiser_id']
            url_keywords = "https://api.mercadolibre.com/advertising/advertisers/{0}/brand_ads/campaigns/{1}/keywords".format(advertiser_id, camp_id, date_ago, today)
            res_keywords = requests.get(url_keywords, headers=headers)
            data_response_keywords = res_keywords.json()
            result = []
            if res_keywords.status_code == 200:
                url_keywords_metrics = "https://api.mercadolibre.com/advertising/advertisers/{0}/brand_ads/campaigns/{1}/keywords/metrics?date_from={2}&date_to={3}&limit=100".format(advertiser_id, camp_id, date_ago, today)
                res_keywords_metrics = requests.get(url_keywords_metrics, headers=headers)
                data_response_keywords_metrics = res_keywords_metrics.json()
                if res_keywords_metrics.status_code == 200:
                    dict_keywords = {item["keyword"]: item for item in data_response_keywords_metrics['summary']}
                    lista_combinada = []
                    for item in data_response_keywords:
                        keyword = item["term"]  # Tomamos el término de lista1
                        if keyword in dict_keywords:
                            item_modificado = {**item, "max_cpc": item["cpc"]}
                            del item_modificado["cpc"]
                            # Fusionamos los datos de ambas listas
                            combinado = {**item_modificado, **dict_keywords[keyword]}
                            lista_combinada.append(combinado)
                    def format_currency(value):
                        return "${:,.2f}".format(value)
                    for key in lista_combinada:    
                        term_key = key.get('keyword')
                        if len(term_key) > 20:
                            term_key = term_key[:20] + "..."
                        result.append({
                            'term': term_key,
                            'cpc_max': format_currency(key.get('max_cpc')),
                            'cpc': format_currency(key.get('cpc')),
                            'prints': key.get('prints'),
                            'clics': key.get('clics'),
                            'units_quantity': key.get('event_time').get('units_quantity'),
                            'cvr': key.get('cvr'),
                            'units_amount': key.get('event_time').get('units_amount'), 
                            'ctr': key.get('ctr'), 
                            'consumed_budget': format_currency(key.get('consumed_budget')), 
                            'acos': key.get('acos')
                        })
                    print("LISTA ",lista_combinada)
                    print("RESULT ",result)
                    return result
                elif res_keywords_metrics.status_code == 401:
                    print(f"Error {res_keywords_metrics.status_code}: {res_keywords_metrics.text}")
                    raise UserError(f"Error getting data from API: {data_response_keywords_metrics['message']}, refresh access token to continue")     
                else:
                    print(f"Error {res_keywords_metrics.status_code}: {res_keywords_metrics.text}")
                    raise UserError(f"Error getting data from API: {data_response_keywords_metrics['message']}")
            elif res_keywords.status_code == 401:
                print(f"Error {res_keywords.status_code}: {res_keywords.text}")
                raise UserError(f"Error getting data from API: {data_response_keywords['message']}, refresh access token to continue")     
            else:
                print(f"Error {res_keywords.status_code}: {res_keywords.text}")
                raise UserError(f"Error getting data from API: {data_response_keywords['message']}")              
        elif res_advertiser.status_code == 401:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}, refresh access token to continue")
        else:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}")

class VexMeliDisplay(models.Model):
    _name               = "vex.meli.display"
    _description        = "Model for Display meli advertiser's campaigns"

    @api.model
    def get_latest_campaigns(self, option):
        today = datetime.today().date()
        if option == "7":
            date_ago = today - relativedelta(days=7)
        elif option == "15":
            date_ago = today - relativedelta(days=15)
        elif option == "30":
            date_ago = today - relativedelta(days=30)
        elif option == "60":
            date_ago = today - relativedelta(days=60)
        elif option == "90":
            date_ago = today - relativedelta(days=90)

        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        
        ACCESS_TOKEN = meli_instance.access_token
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}",
                   "api-version": "2"}
        url_advertiser = f"https://api.mercadolibre.com/advertising/advertisers?product_id=DISPLAY"
        res_advertiser = requests.get(url_advertiser, headers=headers)
        data_response_advertiser = res_advertiser.json()
        if res_advertiser.status_code == 200:
            advertiser_id = data_response_advertiser['advertisers'][0]['advertiser_id']
            url_campaigns = "https://api.mercadolibre.com/advertising/advertisers/{0}/display/campaigns".format(advertiser_id)
            res_campaigns = requests.get(url_campaigns, headers=headers)
            data_response_campaigns = res_campaigns.json()
            result = []
            if res_campaigns.status_code == 200:
                for camp in data_response_campaigns['results']:
                    campaign_id = camp.get('id')
                    url_campaigns_metrics = "https://api.mercadolibre.com/advertising/advertisers/{0}/display/campaigns/{1}/metrics?date_from={2}&date_to={3}".format(advertiser_id, campaign_id, date_ago, today)
                    res_campaigns_metrics = requests.get(url_campaigns_metrics, headers=headers)
                    data_response_campaigns_metrics = res_campaigns_metrics.json()
                    if res_campaigns_metrics.status_code == 200:
                        name_camp = camp.get('name')
                        if len(name_camp) > 20:
                            name_camp = name_camp[:20] + "..."
                        result.append({
                            'id': camp.get('id'),
                            'name': name_camp,
                            'status': camp.get('status'),
                            'start_date': camp.get('start_date').split("T")[0],
                            'end_date': camp.get('end_date').split("T")[0],
                            'prints': data_response_campaigns_metrics.get('summary').get('prints'),
                            'clicks': data_response_campaigns_metrics.get('summary').get('clicks'),
                            'ctr': data_response_campaigns_metrics.get('summary').get('ctr'),
                            'reach': data_response_campaigns_metrics.get('summary').get('reach'), 
                            'average_frequency': data_response_campaigns_metrics.get('summary').get('average_frequency'), 
                        })
                    elif res_campaigns_metrics.status_code == 401:
                        print(f"Error {res_campaigns_metrics.status_code}: {res_campaigns_metrics.text}")
                        raise UserError(f"Error getting data from API: {data_response_campaigns_metrics['message']}, refresh access token to continue")     
                    else:
                        print(f"Error {res_campaigns_metrics.status_code}: {res_campaigns_metrics.text}")
                        raise UserError(f"Error getting data from API: {data_response_campaigns_metrics['message']}")
                return result 
            elif res_campaigns.status_code == 401:
                print(f"Error {res_campaigns.status_code}: {res_campaigns.text}")
                raise UserError(f"Error getting data from API: {data_response_campaigns['message']}, refresh access token to continue")     
            else:
                print(f"Error {res_campaigns.status_code}: {res_campaigns.text}")
                raise UserError(f"Error getting data from API: {data_response_campaigns['code']}")              
        elif res_advertiser.status_code == 401:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}, refresh access token to continue")
        else:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}")

    @api.model
    def get_latest_lineitems(self, camp_id, option):
        today = datetime.today().date()
        if option == "7":
            date_ago = today - relativedelta(days=7)
        elif option == "15":
            date_ago = today - relativedelta(days=15)
        elif option == "30":
            date_ago = today - relativedelta(days=30)
        elif option == "60":
            date_ago = today - relativedelta(days=60)
        elif option == "90":
            date_ago = today - relativedelta(days=90)

        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        
        ACCESS_TOKEN = meli_instance.access_token
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}",
                   "api-version": "2"}
        url_advertiser = f"https://api.mercadolibre.com/advertising/advertisers?product_id=DISPLAY"
        res_advertiser = requests.get(url_advertiser, headers=headers)
        data_response_advertiser = res_advertiser.json()
        if res_advertiser.status_code == 200:
            advertiser_id = data_response_advertiser['advertisers'][0]['advertiser_id']
            url_lineitems = "https://api.mercadolibre.com/advertising/advertisers/{0}/display/campaigns/{1}/line_items".format(advertiser_id, camp_id)
            res_lineitems = requests.get(url_lineitems, headers=headers)
            data_response_lineitems = res_lineitems.json()
            result = []
            if res_lineitems.status_code == 200:
                url_lineitems_metrics = "https://api.mercadolibre.com/advertising/advertisers/{0}/display/metrics?dimension=line_items&date_from={1}&date_to={2}&campaign_id={3}".format(advertiser_id, date_ago, today,camp_id)
                res_lineitems_metrics = requests.get(url_lineitems_metrics, headers=headers)
                data_response_lineitems_metrics = res_lineitems_metrics.json()
                if res_lineitems_metrics.status_code == 200:
                    dict_lineitems = {item["line_item_id"]: item for item in data_response_lineitems_metrics}
                    lista_combinada = []
                    for item in data_response_lineitems['results']:
                        line_item_id = item["line_item_id"]
                        if line_item_id in dict_lineitems:
                            lista_combinada.append({**item, **dict_lineitems[line_item_id]})
                        else:
                            lista_combinada.append(item)
                    for i in lista_combinada:    
                        item_name = i.get('name')
                        if len(item_name) > 20:
                            item_name = item_name[:20] + "..."
                        result.append({
                            'id': i.get('line_item_id'),
                            'name': item_name,
                            'status': i.get('status'),
                            'start_date': i.get('start_date').split("T")[0],
                            'end_date': i.get('end_date').split("T")[0],
                            'prints': i.get('summary').get('prints'),
                            'clicks': i.get('summary').get('clicks'), 
                            'ctr': i.get('summary').get('ctr'), 
                        })
                    return result
                elif res_lineitems_metrics.status_code == 401:
                    print(f"Error {res_lineitems_metrics.status_code}: {res_lineitems_metrics.text}")
                    raise UserError(f"Error getting data from API: {data_response_lineitems_metrics['message']}, refresh access token to continue")     
                else:
                    print(f"Error {res_lineitems_metrics.status_code}: {res_lineitems_metrics.text}")
                    raise UserError(f"Error getting data from API: {data_response_lineitems_metrics['message']}")
            elif res_lineitems.status_code == 401:
                print(f"Error {res_lineitems.status_code}: {res_lineitems.text}")
                raise UserError(f"Error getting data from API: {data_response_lineitems['message']}, refresh access token to continue")     
            else:
                print(f"Error {res_lineitems.status_code}: {res_lineitems.text}")
                raise UserError(f"Error getting data from API: {data_response_lineitems}")              
        elif res_advertiser.status_code == 401:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}, refresh access token to continue")
        else:
            print(f"Error {res_advertiser.status_code}: {res_advertiser.text}")
            raise UserError(f"Error getting data from API: {data_response_advertiser['message']}")