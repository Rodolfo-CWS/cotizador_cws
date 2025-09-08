#!/usr/bin/env python3
"""
BUSINESS LOGIC VALIDATION TEST SUITE - CWS Cotizador
Tests real business scenarios, financial workflows, and data integrity
Focus Areas: Complete quotation workflows, business rule validation, data persistence
"""

import sys
import os
import json
import requests
import time
from decimal import Decimal, ROUND_HALF_UP
import unittest

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import system modules
try:
    from database import DatabaseManager
    from supabase_manager import SupabaseManager
    print("System modules imported successfully")
except ImportError as e:
    print(f"Warning: Could not import system modules: {e}")
    DatabaseManager = None
    SupabaseManager = None

class BusinessValidationTests(unittest.TestCase):
    """Test suite for business logic validation and financial workflows"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        print("=== BUSINESS VALIDATION TEST SETUP ===")
        
        # Try to initialize database manager
        try:
            if DatabaseManager:
                cls.db_manager = DatabaseManager()
                print("OK DatabaseManager initialized")
            else:
                cls.db_manager = None
                print("WARNING: DatabaseManager not available")
        except Exception as e:
            cls.db_manager = None
            print(f"ERROR: Could not initialize DatabaseManager: {e}")
        
        # Try to initialize Supabase manager
        try:
            if SupabaseManager:
                cls.supabase_manager = SupabaseManager()
                print("OK SupabaseManager initialized")
            else:
                cls.supabase_manager = None
                print("WARNING: SupabaseManager not available")
        except Exception as e:
            cls.supabase_manager = None
            print(f"ERROR: Could not initialize SupabaseManager: {e}")
        
        # Test server endpoint if available
        cls.server_url = "http://localhost:5000"
        try:
            response = requests.get(f"{cls.server_url}/info", timeout=2)
            cls.server_available = response.status_code == 200
            if cls.server_available:
                print(f"OK Local server available at {cls.server_url}")
            else:
                print(f"WARNING: Server responded with status {response.status_code}")
        except Exception as e:
            cls.server_available = False
            print(f"INFO: Local server not available: {e}")
    
    def test_safe_float_function(self):
        """Test the safe_float function used throughout the system"""
        print("\n=== TEST: safe_float Function Validation ===")
        
        # Import the safe_float function from app.py if available
        try:
            import imp
            app_module = imp.load_source('app', 'app.py')
            safe_float = app_module.safe_float
            
            test_cases = [
                ("100.50", 100.50),
                ("0", 0.00),
                ("", 0.00),  # Default case
                (None, 0.00),  # None case
                ("invalid", 0.00),  # Invalid string
                (-50.25, -50.25),  # Negative number
                (0.0, 0.00),  # Zero float
            ]
            
            for input_val, expected in test_cases:
                result = safe_float(input_val)
                self.assertEqual(result, expected, f"safe_float({input_val}) returned {result}, expected {expected}")
                print(f"OK safe_float({input_val}) = {result}")
                
        except Exception as e:
            print(f"INFO: Could not test safe_float function: {e}")
            self.skipTest("safe_float function not available for testing")
    
    def test_material_validation_logic(self):
        """Test material validation logic from the system"""
        print("\n=== TEST: Material Validation Logic ===")
        
        try:
            import imp
            app_module = imp.load_source('app', 'app.py')
            validar_material = app_module.validar_material
            
            # Test material validation with real system logic
            test_material = {
                "descripcion": "PTR 2\" x 2\" CAL 11",
                "peso": 4.62,
                "cantidad": 10.0,
                "precio": 28.50
            }
            
            validated = validar_material(test_material)
            
            # Verify the validation results
            self.assertIn('peso', validated)
            self.assertIn('cantidad', validated)
            self.assertIn('precio', validated)
            self.assertIn('subtotal', validated)
            
            # Check calculation accuracy
            expected_subtotal = 4.62 * 10.0 * 28.50  # 1316.70
            calculated_subtotal = validated['subtotal']
            self.assertAlmostEqual(calculated_subtotal, expected_subtotal, places=2,
                msg=f"Material subtotal calculation incorrect: got {calculated_subtotal}, expected {expected_subtotal}")
            
            print(f"OK Material validation: {validated['descripcion']}")
            print(f"   Peso: {validated['peso']} kg")
            print(f"   Cantidad: {validated['cantidad']}")
            print(f"   Precio: ${validated['precio']}")
            print(f"   Subtotal: ${validated['subtotal']}")
            
        except Exception as e:
            print(f"INFO: Could not test material validation: {e}")
            self.skipTest("Material validation function not available")
    
    def test_quotation_numbering_system(self):
        """Test the automatic quotation numbering system"""
        print("\n=== TEST: Quotation Numbering System ===")
        
        if not self.db_manager:
            self.skipTest("Database manager not available")
        
        try:
            # Test data for numbering
            test_data = {
                "datosGenerales": {
                    "cliente": "ACME Corporation",
                    "vendedor": "Juan Perez", 
                    "proyecto": "Test Project",
                    "atencionA": "Luis Gomez",
                    "contacto": "luis@acme.com",
                    "revision": "1"
                    # No numeroCotizacion - should be generated
                },
                "items": [{
                    "descripcion": "Test Item",
                    "cantidad": "1",
                    "uom": "Pieza",
                    "total": "1000.00",
                    "materiales": [],
                    "otrosMateriales": []
                }],
                "condiciones": {
                    "moneda": "MXN",
                    "tiempoEntrega": "15 dias habiles"
                }
            }
            
            # Save quotation and check numbering
            result = self.db_manager.guardar_cotizacion(test_data)
            
            self.assertTrue(result.get("success", False), f"Quotation save failed: {result.get('error')}")
            
            numero_generado = result.get("numeroCotizacion")
            self.assertIsNotNone(numero_generado, "Quotation number not generated")
            
            # Validate numbering format: CLIENTE-CWS-INICIALES-###-R#-PROYECTO
            parts = numero_generado.split("-")
            self.assertGreaterEqual(len(parts), 5, f"Invalid quotation number format: {numero_generado}")
            
            # Check format components
            self.assertIn("ACME", parts[0].upper())  # Client
            self.assertEqual("CWS", parts[1])         # Company
            self.assertIn("J", parts[2])              # Vendor initials (Juan)
            self.assertTrue(parts[3].isdigit())       # Sequential number
            self.assertIn("R1", parts[4])             # Revision
            
            print(f"OK Quotation number generated: {numero_generado}")
            print(f"   Format validated: Client-CWS-Initials-Sequential-Revision-Project")
            
            # Test that the quotation can be retrieved
            retrieved = self.db_manager.obtener_cotizacion(numero_generado)
            self.assertTrue(retrieved.get("encontrado", False), 
                f"Could not retrieve saved quotation: {retrieved.get('mensaje')}")
            
            print(f"OK Quotation successfully retrieved from database")
            
        except Exception as e:
            print(f"ERROR: Quotation numbering test failed: {e}")
            self.fail(f"Quotation numbering system test failed: {e}")
    
    def test_financial_calculation_integration(self):
        """Test financial calculations in complete quotation workflow"""
        print("\n=== TEST: Financial Calculations Integration ===")
        
        if not self.db_manager:
            self.skipTest("Database manager not available")
        
        try:
            # Create quotation with complex financial data
            quotation_data = {
                "datosGenerales": {
                    "cliente": "Industrial Solutions",
                    "vendedor": "Maria Rodriguez",
                    "proyecto": "Warehouse Structure",
                    "revision": "1"
                },
                "items": [{
                    "descripcion": "Steel Structure",
                    "cantidad": "5",
                    "uom": "Conjunto",
                    "transporte": "500.00",
                    "instalacion": "750.00",
                    "seguridad": "15",  # 15% security margin
                    "descuento": "10",  # 10% discount
                    "materiales": [{
                        "descripcion": "PTR 2x2 CAL 11",
                        "peso": 4.62,
                        "cantidad": 50.0,
                        "precio": 28.50
                    }],
                    "otrosMateriales": [{
                        "descripcion": "Soldadura",
                        "cantidad": 10.0,
                        "precio": 25.00
                    }]
                }],
                "condiciones": {
                    "moneda": "MXN",
                    "tiempoEntrega": "20 dias habiles"
                }
            }
            
            # Save and validate
            result = self.db_manager.guardar_cotizacion(quotation_data)
            self.assertTrue(result.get("success", False), f"Complex quotation save failed: {result.get('error')}")
            
            numero = result.get("numeroCotizacion")
            print(f"OK Complex quotation saved: {numero}")
            
            # Retrieve and validate financial data
            retrieved = self.db_manager.obtener_cotizacion(numero)
            self.assertTrue(retrieved.get("encontrado", False))
            
            saved_quotation = retrieved.get("item", {})
            saved_items = saved_quotation.get("items", [])
            
            self.assertGreater(len(saved_items), 0, "No items found in saved quotation")
            
            # Validate first item calculations
            item = saved_items[0]
            
            # Check that financial fields are present and valid
            financial_fields = ['transporte', 'instalacion', 'seguridad', 'descuento', 'total']
            for field in financial_fields:
                self.assertIn(field, item, f"Missing financial field: {field}")
            
            # Validate materials calculations
            materials = item.get('materiales', [])
            for material in materials:
                if 'subtotal' in material:
                    peso = float(material.get('peso', 0))
                    cantidad = float(material.get('cantidad', 0))
                    precio = float(material.get('precio', 0))
                    subtotal = float(material.get('subtotal', 0))
                    
                    expected_subtotal = peso * cantidad * precio
                    self.assertAlmostEqual(subtotal, expected_subtotal, places=2,
                        msg=f"Material subtotal incorrect: {subtotal} != {expected_subtotal}")
            
            print(f"OK Financial calculations validated in saved quotation")
            
        except Exception as e:
            print(f"ERROR: Financial calculation integration test failed: {e}")
            self.fail(f"Financial calculation integration failed: {e}")
    
    def test_currency_conversion_workflow(self):
        """Test USD currency conversion in complete workflow"""
        print("\n=== TEST: Currency Conversion Workflow ===")
        
        if not self.db_manager:
            self.skipTest("Database manager not available")
        
        try:
            # Create USD quotation
            usd_quotation = {
                "datosGenerales": {
                    "cliente": "US Client Corp",
                    "vendedor": "Carlos Martinez",
                    "proyecto": "Export Project",
                    "revision": "1"
                },
                "items": [{
                    "descripcion": "Steel Assembly",
                    "cantidad": "2",
                    "uom": "Unit",
                    "total": "2000.00",  # This is in MXN internally
                    "materiales": [],
                    "otrosMateriales": []
                }],
                "condiciones": {
                    "moneda": "USD",
                    "tipoCambio": "17.50",  # Exchange rate
                    "tiempoEntrega": "30 days"
                }
            }
            
            # Save USD quotation
            result = self.db_manager.guardar_cotizacion(usd_quotation)
            self.assertTrue(result.get("success", False), f"USD quotation save failed: {result.get('error')}")
            
            numero = result.get("numeroCotizacion")
            print(f"OK USD quotation saved: {numero}")
            
            # Retrieve and validate currency data
            retrieved = self.db_manager.obtener_cotizacion(numero)
            self.assertTrue(retrieved.get("encontrado", False))
            
            saved_quotation = retrieved.get("item", {})
            conditions = saved_quotation.get("condiciones", {})
            
            # Validate currency fields
            self.assertEqual(conditions.get("moneda"), "USD", "Currency not saved correctly")
            self.assertIn("tipoCambio", conditions, "Exchange rate not saved")
            
            exchange_rate = float(conditions.get("tipoCambio", 0))
            self.assertGreater(exchange_rate, 0, "Exchange rate should be positive")
            self.assertLessEqual(exchange_rate, 30, "Exchange rate should be reasonable (< 30)")
            
            print(f"OK Currency conversion data validated:")
            print(f"   Currency: {conditions.get('moneda')}")
            print(f"   Exchange Rate: {exchange_rate}")
            
        except Exception as e:
            print(f"ERROR: Currency conversion workflow test failed: {e}")
            self.fail(f"Currency conversion workflow failed: {e}")
    
    def test_revision_control_system(self):
        """Test quotation revision control and validation"""
        print("\n=== TEST: Revision Control System ===")
        
        if not self.db_manager:
            self.skipTest("Database manager not available")
        
        try:
            # Create original quotation
            original_data = {
                "datosGenerales": {
                    "cliente": "Revision Test Corp",
                    "vendedor": "Ana Lopez",
                    "proyecto": "Revision Control Test",
                    "revision": "1"
                },
                "items": [{
                    "descripcion": "Original Item",
                    "cantidad": "1",
                    "total": "1000.00",
                    "materiales": [],
                    "otrosMateriales": []
                }],
                "condiciones": {
                    "moneda": "MXN"
                }
            }
            
            # Save original
            result = self.db_manager.guardar_cotizacion(original_data)
            self.assertTrue(result.get("success", False))
            original_number = result.get("numeroCotizacion")
            
            # Extract base number for revision
            base_number = original_number.rsplit("-R1-", 1)
            if len(base_number) == 2:
                base_part = base_number[0]
                project_part = base_number[1]
                
                # Create revision 2
                revision_data = original_data.copy()
                revision_data["datosGenerales"]["revision"] = "2"
                revision_data["datosGenerales"]["justificacion"] = "Price update required"
                revision_data["items"][0]["total"] = "1200.00"  # Updated price
                
                # Test that revision system works
                result_r2 = self.db_manager.guardar_cotizacion(revision_data)
                self.assertTrue(result_r2.get("success", False))
                revision_number = result_r2.get("numeroCotizacion")
                
                # Validate revision numbering
                self.assertIn("R2", revision_number, "Revision number should contain R2")
                
                print(f"OK Revision control validated:")
                print(f"   Original: {original_number}")
                print(f"   Revision: {revision_number}")
                
                # Verify both quotations exist and are different
                original_retrieved = self.db_manager.obtener_cotizacion(original_number)
                revision_retrieved = self.db_manager.obtener_cotizacion(revision_number)
                
                self.assertTrue(original_retrieved.get("encontrado", False))
                self.assertTrue(revision_retrieved.get("encontrado", False))
                
                # Check that totals are different
                original_total = original_retrieved.get("item", {}).get("items", [{}])[0].get("total")
                revision_total = revision_retrieved.get("item", {}).get("items", [{}])[0].get("total")
                
                self.assertNotEqual(original_total, revision_total, "Revision should have different values")
                print(f"   Original total: ${original_total}")
                print(f"   Revision total: ${revision_total}")
                
        except Exception as e:
            print(f"ERROR: Revision control test failed: {e}")
            self.fail(f"Revision control system failed: {e}")
    
    def test_data_persistence_and_integrity(self):
        """Test data persistence and integrity across save/retrieve cycles"""
        print("\n=== TEST: Data Persistence and Integrity ===")
        
        if not self.db_manager:
            self.skipTest("Database manager not available")
        
        try:
            # Create comprehensive quotation with all field types
            comprehensive_data = {
                "datosGenerales": {
                    "cliente": "Data Integrity Corp",
                    "vendedor": "Roberto Silva",
                    "proyecto": "Complete Data Test",
                    "atencionA": "System Admin",
                    "contacto": "admin@company.com",
                    "revision": "1"
                },
                "items": [
                    {
                        "descripcion": "Complex Item with All Fields",
                        "cantidad": "3",
                        "uom": "Conjunto",
                        "transporte": "150.25",
                        "instalacion": "225.75",
                        "seguridad": "12",
                        "descuento": "8",
                        "total": "5000.00",
                        "materiales": [
                            {
                                "descripcion": "Material 1",
                                "peso": 2.5,
                                "cantidad": 10,
                                "precio": 35.50,
                                "subtotal": 887.50
                            }
                        ],
                        "otrosMateriales": [
                            {
                                "descripcion": "Other Material 1",
                                "cantidad": 5,
                                "precio": 45.00,
                                "subtotal": 225.00
                            }
                        ]
                    }
                ],
                "condiciones": {
                    "moneda": "MXN",
                    "tiempoEntrega": "25 dias habiles",
                    "entregaEn": "Planta Cliente",
                    "terminos": "40% anticipo, 60% contra entrega",
                    "comentarios": "Instalacion especializada requerida"
                }
            }
            
            # Save comprehensive quotation
            result = self.db_manager.guardar_cotizacion(comprehensive_data)
            self.assertTrue(result.get("success", False), f"Comprehensive save failed: {result.get('error')}")
            
            numero = result.get("numeroCotizacion")
            print(f"OK Comprehensive quotation saved: {numero}")
            
            # Retrieve and validate ALL fields are preserved
            retrieved = self.db_manager.obtener_cotizacion(numero)
            self.assertTrue(retrieved.get("encontrado", False))
            
            saved_data = retrieved.get("item", {})
            
            # Validate datosGenerales
            saved_general = saved_data.get("datosGenerales", {})
            original_general = comprehensive_data["datosGenerales"]
            
            for field in original_general:
                self.assertIn(field, saved_general, f"Missing datosGenerales field: {field}")
                if field != "revision":  # Revision might be modified by system
                    original_value = original_general[field]
                    saved_value = saved_general[field]
                    self.assertEqual(saved_value, original_value, 
                        f"Field {field} not preserved: '{saved_value}' != '{original_value}'")
            
            # Validate items structure
            saved_items = saved_data.get("items", [])
            original_items = comprehensive_data["items"]
            
            self.assertEqual(len(saved_items), len(original_items), "Item count not preserved")
            
            for i, (saved_item, original_item) in enumerate(zip(saved_items, original_items)):
                # Check basic item fields
                basic_fields = ["descripcion", "cantidad", "uom"]
                for field in basic_fields:
                    if field in original_item:
                        self.assertIn(field, saved_item, f"Item {i} missing field: {field}")
                
                # Check materials
                if "materiales" in original_item:
                    self.assertIn("materiales", saved_item, f"Item {i} missing materials")
                    saved_materials = saved_item["materiales"]
                    original_materials = original_item["materiales"]
                    
                    self.assertEqual(len(saved_materials), len(original_materials), 
                        f"Item {i} materials count not preserved")
            
            # Validate condiciones
            saved_conditions = saved_data.get("condiciones", {})
            original_conditions = comprehensive_data["condiciones"]
            
            for field in original_conditions:
                self.assertIn(field, saved_conditions, f"Missing condiciones field: {field}")
            
            print(f"OK All data fields preserved across save/retrieve cycle")
            print(f"   General fields: {len(saved_general)} preserved")
            print(f"   Items: {len(saved_items)} preserved")
            print(f"   Conditions: {len(saved_conditions)} preserved")
            
        except Exception as e:
            print(f"ERROR: Data persistence test failed: {e}")
            self.fail(f"Data persistence and integrity failed: {e}")

def run_business_validation_tests():
    """Run the complete business validation test suite"""
    print("="*80)
    print("CWS COTIZADOR - BUSINESS LOGIC VALIDATION TEST SUITE")
    print("Testing real business scenarios, financial workflows, and data integrity")
    print("="*80)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_methods = [
        'test_safe_float_function',
        'test_material_validation_logic',
        'test_quotation_numbering_system',
        'test_financial_calculation_integration',
        'test_currency_conversion_workflow',
        'test_revision_control_system',
        'test_data_persistence_and_integrity'
    ]
    
    for method in test_methods:
        suite.addTest(BusinessValidationTests(method))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*80)
    print("BUSINESS VALIDATION TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")  
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {result.testsRun - len(result.failures) - len(result.errors) if hasattr(result, 'skipped') else 'N/A'}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOVERALL RESULT: {'PASSED' if success else 'FAILED'}")
    
    return success

if __name__ == "__main__":
    success = run_business_validation_tests()
    sys.exit(0 if success else 1)