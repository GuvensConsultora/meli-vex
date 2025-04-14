from odoo import models, fields
import base64
import openpyxl
import logging
import re
from io import BytesIO

_logger = logging.getLogger(__name__)

class ImportExcelWizard(models.TransientModel):
    _name = 'import.excel.wizard'
    _description = 'Wizard to Import Excel Data'

    excel_file = fields.Binary(string='Excel File', required=True)
    file_name = fields.Char(string='File Name')
    import_type = fields.Selection([
        ('mlm_price', 'XSLX -> MLMXXXXXXXXX/ SKU / Cost in $'),
    ], string='Import Type', required=True)

    def action_import_file(self):
        # Decodificar el archivo binario
        data = base64.b64decode(self.excel_file)
        _logger.info(f"Import Type: {self.import_type}")

        # Leer el archivo Excel usando openpyxl
        workbook = openpyxl.load_workbook(BytesIO(data), data_only=True)
        sheet = workbook.active  # Toma la primera hoja activa

        # Expresión regular para detectar códigos 'MLMXXXXXXXXX'
        mlm_pattern = re.compile(r'MLM\d{9}')

        # Variables para el conteo de datos procesados
        total_lines = 0
        lines_with_less_columns = 0
        lines_without_price = 0
        lines_with_invalid_price = 0
        lines_without_sku_or_mlm = 0
        updated_products_count = 0
        not_found_products_count = 0

        # Iterar por las filas del Excel
        for row in sheet.iter_rows(values_only=True):
            total_lines += 1  # Incrementar el total de líneas procesadas

            # Verificar que la fila tenga exactamente 3 columnas
            if len(row) < 3:
                _logger.warning(f"Row {total_lines} has less than 3 columns, skipping.")
                lines_with_less_columns += 1
                continue

            # Asignar columnas
            mlm_code = row[0]  # Primera columna: Código MLM
            sku_code = row[1]  # Segunda columna: SKU
            price_value = row[2]  # Tercera columna: Precio

            # Validar que al menos una identificación exista (SKU o MLM)
            if not mlm_code and not sku_code:
                _logger.warning(f"Row {total_lines} does not contain a valid SKU or MLM code. Skipping.")
                lines_without_sku_or_mlm += 1
                continue

            # Validar el precio
            if price_value is None:
                _logger.warning(f"Row {total_lines} with SKU '{sku_code}' or MLM Code '{mlm_code}' has no price.")
                lines_without_price += 1
                continue

            # Limpiar el precio
            price_value = str(price_value).replace('$', '').replace(' ', '').strip()

            # Comprobar si el precio es un valor válido
            try:
                price = float(price_value)
            except ValueError:
                _logger.warning(f"Row {total_lines} has invalid price value: '{price_value}'. Skipping.")
                lines_with_invalid_price += 1
                continue

            # Validar si el código MLM tiene el formato correcto
            if mlm_code and not mlm_pattern.match(mlm_code):
                _logger.warning(f"Row {total_lines} has an invalid MLM code format: '{mlm_code}'.")

            # Búsqueda del producto por SKU (prioridad)
            product_template = None
            if sku_code:
                product_template = self.env['product.template'].search([('ml_reference', '=', sku_code)], limit=1)
                if product_template:
                    _logger.info("Precio asignado por sku")

            # Si no se encuentra por SKU, buscar por MLM
            if not product_template and mlm_code:
                product_template = self.env['product.template'].search([('meli_code', '=', mlm_code)], limit=1)
                if product_template:
                    _logger.info("Precio asignado por MLM")

            if product_template:
                # Actualizar el precio
                product_template.write({'standard_price': price})
                _logger.info(f"Product '{product_template.name}' (SKU: '{sku_code}', MLM: '{mlm_code}') updated with price {price}.")
                updated_products_count += 1
            else:
                _logger.info(f"Product not found for SKU: '{sku_code}' or MLM Code: '{mlm_code}'.")
                not_found_products_count += 1

        # Log final con el resumen
        _logger.info(f"Import Summary: {total_lines} total lines processed.")
        _logger.info(f"{lines_with_less_columns} lines skipped due to insufficient columns.")
        _logger.info(f"{lines_without_price} lines skipped due to missing price.")
        _logger.info(f"{lines_with_invalid_price} lines skipped due to invalid price format.")
        _logger.info(f"{lines_without_sku_or_mlm} lines skipped due to missing SKU or MLM code.")
        _logger.info(f"{updated_products_count} products updated, {not_found_products_count} products not found.")

        return {'type': 'ir.actions.act_window_close'}
