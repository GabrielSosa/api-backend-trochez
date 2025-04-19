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
        self.static_dir = self.base_dir.parent / "static"
        
        # Create temp directory if it doesn't exist
        self.temp_dir = self.base_dir.parent / "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Set up Jinja2 environment with custom functions
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        
        # Add a static_url function to the Jinja environment
        self.env.globals['static_url'] = self.static_url
        
        # Set locale for date formatting
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'es_ES')
            except:
                pass  # Fall back to default locale if Spanish is not available
    
    def static_url(self, path):
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
        total_deductions = sum(deduction.amount for deduction in deductions)
        
        # Format currency values
        formatted_total_deductions = f"₡{total_deductions:,}".replace(",", " ")
        formatted_appraisal_value = f"${vehicle_appraisal.appraisal_value_usd:,}".replace(",", " ")
        
        # Convert appraisal value to words - convert Decimal to int
        appraisal_value_int = int(vehicle_appraisal.appraisal_value_usd)
        appraisal_value_words = self.number_to_words(appraisal_value_int)
        
        # Prepare template data
        template_data = {
            "appraisal": vehicle_appraisal,
            "deductions": deductions,
            "formatted_date": formatted_date,
            "total_deductions": formatted_total_deductions,
            "appraisal_value": formatted_appraisal_value,
            "appraisal_value_words": appraisal_value_words
        }
        
        # Render HTML template
        template = self.env.get_template("certificado.html")  # Use the correct filename with 'r'
        html_content = template.render(**template_data)
        
        # Create a temporary file for the PDF
        output_path = self.temp_dir / f"certificate_{vehicle_appraisal.vehicle_appraisal_id}.pdf"
        
        # Generate PDF using WeasyPrint
        base_url = self.base_dir.as_uri()
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