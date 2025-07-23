import os
from pathlib import Path
import tempfile
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import locale

class CertificateService:
    def __init__(self):
        # Set up paths
        self.base_dir = Path(__file__).parent
        self.template_dir = self.base_dir
        self.static_dir = self.base_dir.parent / "static" # Absolute path to app/static
        
        # Create temp directory if it doesn't exist
        self.temp_dir = self.base_dir.parent / "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Set up Jinja2 environment with custom functions
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        
        # Add a static_url function to the Jinja environment
        # --- Change this line to use the new absolute URL function ---
        self.env.globals['static_url'] = self.static_url_absolute
        # --- End Change ---
        self.env.globals['formatted_date'] = self.format_date
        self.env.globals['number_to_words'] = self.number_to_words
        
        # Set locale for date formatting
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'es_ES')
            except:
                pass  # Fall back to default locale if Spanish is not available
    
    # Optional: Keep the old relative path function if needed elsewhere
    # def static_url(self, path):
    #     """Generate a relative URL for static files"""
    #     return f"../static/{path}"
    
    # --- Add this function ---
    def static_url_absolute(self, path):
        """Generate an absolute file:// URL for static files"""
        absolute_path = self.static_dir / path
        # Ensure the path exists and convert to file URI
        if absolute_path.exists():
             return absolute_path.as_uri()
        else:
             # Handle missing file case - maybe return empty string or log warning
             print(f"Warning: Static file not found at {absolute_path}")
             return "" # Or raise an error
    # --- End Add ---

    def format_date(self, date_obj):
        """Generate a URL for static files"""
        return f"../static/{path}"
    
    def generate_certificate_pdf(self, vehicle_appraisal, deductions):
        """
        Generate a PDF certificate for a vehicle appraisal.
        
        Args:
            vehicle_appraisal: Vehicle appraisal data from database
            deductions: List of deductions for this appraisal
            
        Returns:
            Path to the generated PDF file
        """
        # Format date
        appraisal_date = vehicle_appraisal.appraisal_date
        if isinstance(appraisal_date, datetime):
            formatted_date = appraisal_date.strftime("%d %b %Y")
        else:
            formatted_date = datetime.now().strftime("%d %b %Y")
        
        # Calculate total deductions amount
        total_deductions = sum(deduction.amount or 0 for deduction in deductions)
        
        # Format currency values with null handling
        formatted_total_deductions = f"₡{total_deductions:,}".replace(",", " ")
        
        # Handle null appraisal values and bank values
        appraisal_value_usd = vehicle_appraisal.appraisal_value_usd or 0
        bank_value_in_dollars = vehicle_appraisal.bank_value_in_dollars or 0
        
        # Format appraisal value (VALOR SUGERIDO PARA ENTREGA EN DISTRIBUIDORA)
        if appraisal_value_usd > 0:
            formatted_appraisal_value = f"${appraisal_value_usd:,}".replace(",", " ")
            appraisal_value_int = int(appraisal_value_usd)
            appraisal_value_words = self.number_to_words(appraisal_value_int)
        else:
            formatted_appraisal_value = ""
            appraisal_value_words = ""
        
        # Format bank value (VALOR MAXIMO DE GARANTIA BANCARIA)
        if bank_value_in_dollars > 0:
            formatted_bank_value = f"${bank_value_in_dollars:,}".replace(",", " ")
            bank_value_int = int(bank_value_in_dollars)
            bank_value_words = self.number_to_words(bank_value_int)
        else:
            formatted_bank_value = ""
            bank_value_words = ""
        
        # Handle CRC values (apprasail_value_lower_bank)
        if vehicle_appraisal.apprasail_value_lower_bank is not None:
            appraisal_value_crc_raw = vehicle_appraisal.apprasail_value_lower_bank
            formatted_appraisal_value_crc = f"₡{appraisal_value_crc_raw:,}".replace(",", " ")
            appraisal_value_int_crc = int(appraisal_value_crc_raw)
            appraisal_value_words_crc = self.number_to_words(appraisal_value_int_crc)
        else:
            appraisal_value_crc_raw = 0
            formatted_appraisal_value_crc = ""
            appraisal_value_words_crc = ""
        
        # Helper function to handle null values
        def safe_str(value):
            """Convert any value to string, handling None values"""
            if value is None:
                return ""
            return str(value)
        
        # Create safe deductions with null handling
        safe_deductions = []
        for deduction in deductions:
            safe_deduction = type('SafeDeduction', (), {
                'appraisal_deductions_id': deduction.appraisal_deductions_id,
                'vehicle_appraisal_id': deduction.vehicle_appraisal_id,
                'description': safe_str(deduction.description),
                'amount': deduction.amount or 0
            })()
            safe_deductions.append(safe_deduction)
        
        # Create a safe appraisal object with null handling
        safe_appraisal = type('SafeAppraisal', (), {
            'vehicle_appraisal_id': vehicle_appraisal.vehicle_appraisal_id,
            'appraisal_date': vehicle_appraisal.appraisal_date,
            'vehicle_description': safe_str(vehicle_appraisal.vehicle_description),
            'brand': safe_str(vehicle_appraisal.brand),
            'model_year': vehicle_appraisal.model_year,
            'color': safe_str(vehicle_appraisal.color),
            'mileage': vehicle_appraisal.mileage,
            'fuel_type': safe_str(vehicle_appraisal.fuel_type),
            'engine_size': vehicle_appraisal.engine_size,
            'plate_number': safe_str(vehicle_appraisal.plate_number),
            'applicant': safe_str(vehicle_appraisal.applicant),
            'owner': safe_str(vehicle_appraisal.owner),
            'appraisal_value_usd': vehicle_appraisal.appraisal_value_usd,
            'appraisal_value_trochez': vehicle_appraisal.appraisal_value_trochez,
            'vin': safe_str(vehicle_appraisal.vin),
            'engine_number': safe_str(vehicle_appraisal.engine_number),
            'notes': safe_str(vehicle_appraisal.notes),
            'validity_days': vehicle_appraisal.validity_days,
            'validity_kms': vehicle_appraisal.validity_kms,
            'apprasail_value_lower_cost': vehicle_appraisal.apprasail_value_lower_cost,
            'apprasail_value_bank': vehicle_appraisal.apprasail_value_bank,
            'apprasail_value_lower_bank': vehicle_appraisal.apprasail_value_lower_bank,
            'extras': safe_str(vehicle_appraisal.extras),
            'vin_card': safe_str(vehicle_appraisal.vin_card),
            'engine_number_card': safe_str(vehicle_appraisal.engine_number_card),
            'modified_km': vehicle_appraisal.modified_km,
            'extra_value': vehicle_appraisal.extra_value,
            'discounts': vehicle_appraisal.discounts,
            'bank_value_in_dollars': vehicle_appraisal.bank_value_in_dollars,
            'referencia_original': safe_str(vehicle_appraisal.referencia_original),
            'cert': safe_str(vehicle_appraisal.cert)
        })()
        
        # Prepare template data
        template_data = {
            "appraisal": safe_appraisal,
            "deductions": safe_deductions,
            "formatted_date": formatted_date,
            "total_deductions": formatted_total_deductions,
            "appraisal_value": formatted_appraisal_value,
            "appraisal_value_words": appraisal_value_words,
            "bank_value": formatted_bank_value,
            "bank_value_words": bank_value_words,
            "appraisal_value_crc_raw": appraisal_value_crc_raw,
            "appraisal_value_crc": formatted_appraisal_value_crc,
            "appraisal_value_words_crc": appraisal_value_words_crc
        }
        
        # Render HTML template
        template = self.env.get_template("certificado.html")  # Use the correct filename with 'r'
        html_content = template.render(**template_data)
        
        # Create a temporary file for the PDF
        output_path = self.temp_dir / f"certificate_{vehicle_appraisal.vehicle_appraisal_id}.pdf"
        
        # Generate PDF using WeasyPrint
        base_url = self.base_dir.as_uri()
        # --- Modify HTML object creation ---
        # No base_url needed when using absolute file:// URLs for assets
        html = HTML(string=html_content)
        # --- End Modify ---
        HTML(string=html_content, base_url=base_url).write_pdf(
            output_path,
            stylesheets=[
                CSS(string='''
                    @page {
                        size: A4;
                        margin: 0;
                    }
                    body {
                        margin: 0;
                        padding: 0;
                    }
                ''')
            ]
        )
        
        return output_path
    
    def number_to_words(self, number):
        """Convert a number to words in Spanish."""
        units = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
        teens = ['DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISEIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE']
        tens = ['', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
        
        if number == 0:
            return 'CERO'
        
        if number < 10:
            return units[number]
        
        if number < 20:
            return teens[number - 10]
        
        if number < 100:
            return tens[number // 10] + (' Y ' + units[number % 10] if number % 10 != 0 else '')
        
        if number < 1000:
            hundreds = 'CIEN' if number == 100 else 'CIENTO' if number < 200 else 'DOSCIENTOS' if number < 300 else 'TRESCIENTOS' if number < 400 else 'CUATROCIENTOS' if number < 500 else 'QUINIENTOS' if number < 600 else 'SEISCIENTOS' if number < 700 else 'SETECIENTOS' if number < 800 else 'OCHOCIENTOS' if number < 900 else 'NOVECIENTOS'
            return hundreds + (' ' + self.number_to_words(number % 100) if number % 100 != 0 else '')
        
        if number < 1000000:
            return ('UN MIL' if number < 2000 else self.number_to_words(number // 1000) + ' MIL') + (' ' + self.number_to_words(number % 1000) if number % 1000 != 0 else '')
        
        # For simplicity, we'll just handle up to millions
        return ('UN MILLÓN' if number < 2000000 else self.number_to_words(number // 1000000) + ' MILLONES') + (' ' + self.number_to_words(number % 1000000) if number % 1000000 != 0 else '')