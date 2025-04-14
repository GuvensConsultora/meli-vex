from odoo import models,fields, api
import requests
import json
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import date
_logger = logging.getLogger(__name__)


class VexSolucionesExportProduct(models.TransientModel):
    _name = "vex.export.product.wizard"
    _description = "Wizard Model to export mass product"

    # def get_products_to_export(self):
    #     product_ids = self.env['product.template'].search([('export_to_meli','=', True), ('active','=',True)])
    #     product_to_export = []
    #     for product in product_ids:
    #         # quant_id = self.env['stock.quant'].search([('product_id','=',product.id)], limit=1)
    #         obj={}
    #         obj['name'] = product.name
    #         obj['product_id'] = product.id
    #         obj['quantity'] = product.qty_available
    #         obj['price_unit'] = product.list_price
    #         obj['price_new'] = product.list_price
    #         obj['categ_id'] = product.categ_id.id
    #         obj['meli_category_code'] = product.meli_category_code
    #         obj['num_publication'] = product.ml_publication_code
    #         obj['action_export'] = product.action_export
    #         product_to_export.append((0,0,obj))
    #     return product_to_export

    @api.onchange('export_product_ids')
    def _onchange_export_product_ids(self):
        contador = 0
        for item in self.export_product_ids:
            if item.select_product:
                contador +=1
        _logger.info(f"\n\n\n\n\n{contador}")
        self.items_to_export = contador


    items_to_export = fields.Integer('Items to export', readonly=True)
    export_product_ids = fields.Many2many('vex.export.product.line.wizard', string='export_product') #, default=get_products_to_export
    
    vex_instance_id = fields.Many2one('vex.instance', string='Instance', required=True)
    export_images = fields.Boolean('Do you want to export Images?')
    export_stock = fields.Boolean('Do you want to export Stock?')
    export_price = fields.Boolean('Do you want to export Pricing?')
    ckeck = fields.Selection([
        ('all', 'All'),
        ('not_all', 'Not all')
    ], string='Select the products?', default="all")

    increase_or_discount = fields.Selection([
    ('increase', 'Aumento'),
    ('discount', 'Descuento')
    ], string='Aumento/Descuento')
    amount = fields.Integer('Monto')
    type_amount = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('number', 'Numero')
    ], string='Tipo de monto')

    category_ids = fields.Many2many('product.category', string='category')

    type_product = fields.Selection([
        ('all', 'Todos'),
        ('gold_pro', 'Gold pro'),
        ('gold_special','Gold special')
    ], string='Tipo de producto', default='all')

    massive_action = fields.Boolean(string='Activar accion masiva?', default=False)

    @api.onchange('ckeck')
    def _onchange_ckeck(self):
        if self.ckeck == 'all':
            self.select_all()
        elif self.ckeck == 'not_all':
            self.deselect_all()

    @api.depends('export_product_ids')
    def select_all(self):
        for product in self.export_product_ids:
            product.select_product = True

    @api.depends('export_product_ids')
    def deselect_all(self):
        for product in self.export_product_ids:
            product.select_product = False
    
    @api.onchange('massive_action')
    def _onchange_massive_action(self):
        if self.massive_action:
            if not self.increase_or_discount:
                raise ValidationError("Seleccione un aumento o descuento.")
            if self.amount <= 0:
                raise ValidationError("Ingrese un monto valido. No puede ser menor o igual a 0")
            if not self.type_amount:
                raise ValidationError("Ingrese un tipo de monto.")
            
            # Calculando linea de productos
            for product_id in self.export_product_ids:
                product_id.price_new = self.calculate_mass_action(self.increase_or_discount, self.amount, self.type_amount, product_id.price_unit)
        else:
            # Calculando linea de productos
            for product_id in self.export_product_ids:
                product_id.price_new = product_id.price_unit
    
    @api.onchange('type_product', 'category_ids')
    def _onchange_type_product_category_ids(self):
        if self.type_product is not False:
            type_product = self.type_product
            category_ids = self.category_ids

            # Logica de filtrado:
            # Filtrar registros basados en type_product y category_ids
            domain = []

            domain.append(('export_to_meli','=', True))
            domain.append(('active','=',True))

            if category_ids:
                domain.append(('categ_id', 'in', category_ids.ids))
            if type_product == 'gold_pro':
                domain.append(('listing_type_id','=','gold_pro'))
            elif type_product == 'gold_special':
                domain.append(('listing_type_id','=','gold_special'))

            product_ids = self.env['product.template'].search(domain)
            product_to_export = []

            for product in product_ids:
                obj={}
                obj['name'] = product.name
                obj['product_id'] = product.id
                obj['quantity'] = product.qty_available
                obj['price_unit'] = product.list_price
                obj['price_new'] = product.list_price
                obj['categ_id'] = product.categ_id.id
                obj['meli_category_code'] = product.meli_category_code
                obj['num_publication'] = product.ml_publication_code
                obj['action_export'] = product.action_export
                obj['listing_type_id'] = product.listing_type_id
                obj['ml_reference'] = product.ml_reference
                product_to_export.append(obj)

            # Eliminar todos los datos de export_product_ids
            self.export_product_ids.unlink()

            # Agregar los productos obtenidos a export_product_ids
            self.export_product_ids = [(0, 0, vals) for vals in product_to_export]
            self.type_product = type_product
            self.category_ids = category_ids

    
    def calculate_mass_action(self, action, amount, type_amount, price):
        if action == 'increase':
            if type_amount == 'percentage':
                return price + (price * amount/100)
            else:
                return price + amount
        elif action == 'discount':
            if type_amount == 'percentage':
                return price - (price * amount/100)
            else:
                return price - amount


    def _create_or_update_stock(self, product_id, stock_qty):
        location_id = self.env.ref('odoo-mercadolibre.ml_stock').id
        existing_quant = self.env['stock.quant'].search([
            ('product_id', '=', product_id.id),
            ('location_id', '=', location_id)
        ])
        if existing_quant:
            existing_quant.write({'inventory_quantity': stock_qty})
            existing_quant.action_apply_inventory()
        else:
            self.env['stock.quant'].create({
                'product_id': product_id.id,
                'location_id': location_id,
                'quantity': stock_qty,
            })

    def export(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Bearer {self.vex_instance_id.access_token}'}
        publication_exist = False
        for item in self.export_product_ids:
            if item.select_product:
                if item.action_export == 'edit':
                    obj={}
                    if self.export_stock:
                        obj['available_quantity']=item.quantity  
                    if self.export_price:
                        obj['price']=item.price_new    
                                          
                    try:
                        print("gaa:",item.product_id.ml_publication_code)
                        url_item = f"https://api.mercadolibre.com/items/{item.product_id.ml_publication_code}"
                        response_item = requests.put(url_item, headers=headers, data=json.dumps(obj))
                        print('edit:', response_item.status_code)
                        print('Response content edit:', response_item.content)
                        if response_item.status_code == 200:
                            product_modification_id =  self.env['product.template'].search([('id','=',item.product_id.id)],limit=1)

                            product_modification_id.write({'list_price':item.price_new,})

                            # Modificando stock
                            if self.export_price:
                                stock_qty = item.quantity    
                                stock_product_id=self.env['product.product'].search([('product_tmpl_id','=', product_modification_id.id),('active','=',True)])
                                self._create_or_update_stock(stock_product_id, stock_qty)

                            self.env['vex.meli.logs'].create({
                                'action_type':'Edition',
                                'start_date':date.today(),
                                'state':'done',
                                'description':f"Publication {item.num_publication} was succesfully edited to {obj} ",
                                'vex_restapi_list_id':self.env.ref('odoo-mercadolibre.meli_action_products').id
                            })
                        else:
                            self.env['vex.meli.logs'].create({
                                'action_type':'Edition',
                                'start_date':date.today(),
                                'state':'error',
                                'description':f"Publication {item.num_publication} was failed edited to {obj} ",
                                'vex_restapi_list_id':self.env.ref('odoo-mercadolibre.meli_action_products').id
                            })                                   

                    except Exception as ex:
                        print("Exception %s", ex)     
                else:
                    
                    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                    
                    foto_main = False
                    
                    if item.product_id.attachment_id:
                        foto_main = f"{base_url}/web/content/{item.product_id.attachment_id.id}"

                    json_obj = {}
                    json_obj["title"]=item.name
                    json_obj["category_id"]=item.meli_category_code
                    json_obj["price"]=item.price_unit
                    json_obj["currency_id"]="ARS"
                    json_obj["available_quantity"]=item.quantity if self.export_stock else 0
                    json_obj["buying_mode"]="buy_it_now"
                    json_obj["condition"]="new"
                    json_obj["listing_type_id"]="gold_special"
                    json_obj["pictures"] = [{'source': foto_main}] if foto_main else []
                    json_obj["sale_terms"]=[]
                    json_obj["attributes"]=[{"id": "SELLER_SKU", "value_name": item.ml_reference}] if item.ml_reference else []
                    
                    _logger.info("json_obj: ", json_obj)
                    
                    try:
                        url_item = f"https://api.mercadolibre.com/items"
                        response_item = requests.post(url_item, headers=headers, json=json_obj)
                        if response_item.status_code == 201:
                            response_item = json.loads(response_item.text)
                            item.product_id.write({
                                'action_export': 'edit',
                                'default_code': response_item['id'],
                                'ml_publication_code': response_item['id']  if item.ml_reference else '',
                                'ml_reference': item.ml_reference,
                                'detailed_type': 'product',
                                'inventory_id': response_item['inventory_id'],
                                'buying_mode': response_item['buying_mode'],
                                'thumbnail': response_item['thumbnail'],
                                'meli_code': response_item['id'],
                                'listing_type_id': response_item['listing_type_id'],                 
                                'condition': response_item['condition'],
                                'permalink': response_item['permalink'],
                            })
                        else:
                            _logger.error("Fallo el subir producti:%s", response_item.content)  
                    except Exception as ex:
                        _logger.error("Exception:%s", str(ex))      


class VexSolucionesExportProductLine(models.TransientModel):
    _name = "vex.export.product.line.wizard"
    _description = "Wizard Model to show products line to export to MELI"

    select_product = fields.Boolean('', default=True)
    name = fields.Char('Product')
    product_id = fields.Many2one('product.template', string='product')
    quantity = fields.Float('quantity')
    price_unit = fields.Float('price_unit')
    price_new = fields.Float('Price new')
    categ_id = fields.Many2one('product.category', string='categ')
    meli_category_code = fields.Char('Codigo Categoría ML')
    num_publication = fields.Char('num_publication')
    action_export = fields.Selection([
        ('edit', 'Edition'),
        ('create', 'Creation')
    ], string='Action')
    listing_type_id = fields.Char('Listing Type')
    ml_reference = fields.Char("MELI SKU")