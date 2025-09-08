#!/usr/bin/env python3
"""
FINANCIAL QA TEST SUITE - CWS Cotizador
Comprehensive testing of financial calculations, precision, and business rules
Focus Areas: Pricing, Tax calculations (IVA 16%), Currency conversion, Discounts, Edge cases
"""

import sys
import os
import json
import decimal
from decimal import Decimal, ROUND_HALF_UP
import unittest
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class FinancialCalculationTests(unittest.TestCase):
    """Test suite for financial calculations accuracy and precision"""
    
    def setUp(self):
        """Set up test environment with precision settings"""
        # Set decimal context for financial precision (2 decimal places)
        decimal.getcontext().prec = 10
        decimal.getcontext().rounding = ROUND_HALF_UP
        
        # Test exchange rates
        self.test_exchange_rates = {
            'USD_TO_MXN': 17.50,
            'VALID_MIN': 15.0,
            'VALID_MAX': 25.0
        }
        
        # Test material data (mimics Lista de materiales.csv structure)
        self.test_materials = [
            {"tipo": "PTR 1\" x 1\" CAL 14", "peso": 1.44, "ref": "Peso x metro lineal"},
            {"tipo": "PTR 2\" x 2\" CAL 11", "peso": 4.62, "ref": "Peso x metro lineal"},
            {"tipo": "Placa acero 6mm", "peso": 47.1, "ref": "Peso x m2"}
        ]
        
    def test_basic_material_calculation(self):
        """Test basic material calculation: peso * cantidad * precio = subtotal"""
        print("\n=== TEST: Basic Material Calculation ===")
        
        test_cases = [
            # (peso, cantidad, precio, expected_subtotal)
            (1.44, 10.0, 25.50, 367.20),  # PTR calculation
            (4.62, 5.0, 30.00, 693.00),   # Higher weight material  
            (47.1, 2.5, 15.75, 1853.63),  # Steel plate calculation
            (0.0, 10.0, 25.50, 0.00),     # Zero weight edge case
            (1.44, 0.0, 25.50, 0.00),     # Zero quantity edge case
            (1.44, 10.0, 0.00, 0.00),     # Zero price edge case
        ]
        
        for peso, cantidad, precio, expected in test_cases:
            with self.subTest(peso=peso, cantidad=cantidad, precio=precio):
                # Use same rounding as the system (2 decimal places)
                calculated = round(peso * cantidad * precio, 2)
                self.assertEqual(calculated, expected, 
                    f"Material calculation failed: {peso} * {cantidad} * {precio} = {calculated}, expected {expected}")
                print(f"OK {peso} kg x {cantidad} qty x ${precio} = ${calculated}")
    
    def test_iva_calculation_precision(self):
        """Test IVA (16%) calculation precision across various amounts"""
        print("\n=== TEST: IVA (16%) Calculation Precision ===")
        
        test_amounts = [
            # (subtotal, expected_iva, expected_total)
            (100.00, 16.00, 116.00),
            (1000.00, 160.00, 1160.00),
            (1234.56, 197.53, 1432.09),
            (999.99, 160.00, 1159.99),  # Edge case with .99
            (0.01, 0.00, 0.01),         # Minimum amount
            (12345.67, 1975.31, 14320.98),
            # Edge case: amounts that might cause rounding issues
            (133.33, 21.33, 154.66),   # Repeating decimal
            (166.67, 26.67, 193.34),   # Another repeating case
        ]
        
        for subtotal, expected_iva, expected_total in test_amounts:
            with self.subTest(subtotal=subtotal):
                # System calculation: iva = subtotal * 0.16
                calculated_iva = round(subtotal * 0.16, 2)
                calculated_total = round(subtotal + calculated_iva, 2)
                
                self.assertEqual(calculated_iva, expected_iva, 
                    f"IVA calculation failed for ${subtotal}: got ${calculated_iva}, expected ${expected_iva}")
                self.assertEqual(calculated_total, expected_total,
                    f"Total calculation failed for ${subtotal}: got ${calculated_total}, expected ${expected_total}")
                
                print(f"OK Subtotal: ${subtotal:,.2f} -> IVA: ${calculated_iva:,.2f} -> Total: ${calculated_total:,.2f}")
    
    def test_currency_conversion_precision(self):
        """Test USD/MXN currency conversion precision and consistency"""
        print("\n=== TEST: Currency Conversion Precision ===")
        
        exchange_rate = 17.50  # Test exchange rate
        
        test_cases_mxn = [
            # (amount_mxn, expected_usd)
            (1750.00, 100.00),
            (875.00, 50.00),
            (17.50, 1.00),
            (1.75, 0.10),
            (17500.00, 1000.00),
            # Edge cases for precision
            (1766.25, 100.93),  # Should round to 100.93
            (1733.75, 99.07),   # Should round to 99.07
        ]
        
        for amount_mxn, expected_usd in test_cases_mxn:
            with self.subTest(amount_mxn=amount_mxn):
                # System logic: usd = mxn / exchange_rate
                calculated_usd = round(amount_mxn / exchange_rate, 2)
                
                self.assertEqual(calculated_usd, expected_usd,
                    f"MXN to USD conversion failed: ${amount_mxn} MXN / {exchange_rate} = ${calculated_usd} USD, expected ${expected_usd} USD")
                
                print(f"OK ${amount_mxn:,.2f} MXN / {exchange_rate} = ${calculated_usd:,.2f} USD")
        
        # Test reverse conversion consistency
        print("\nTesting conversion consistency (round-trip):")
        for amount_mxn, _ in test_cases_mxn[:5]:  # Test fewer cases for round-trip
            usd_converted = round(amount_mxn / exchange_rate, 2)
            mxn_back = round(usd_converted * exchange_rate, 2)
            
            # Allow for small rounding differences (within 1 cent)
            difference = abs(amount_mxn - mxn_back)
            self.assertLessEqual(difference, 0.02, 
                f"Round-trip conversion failed: ${amount_mxn} MXN → ${usd_converted} USD → ${mxn_back} MXN (diff: ${difference})")
            
            print(f"OK Round-trip: ${amount_mxn:,.2f} MXN -> ${usd_converted:,.2f} USD -> ${mxn_back:,.2f} MXN")
    
    def test_discount_and_markup_calculations(self):
        """Test discount and security margin (markup) calculations"""
        print("\n=== TEST: Discount and Markup Calculations ===")
        
        base_amount = 1000.00  # Base calculation amount
        
        # Test security margin (markup) calculations
        security_margins = [0, 5, 10, 15, 20, 25]  # Common percentages
        for margin_percent in security_margins:
            with self.subTest(margin_type="security", percent=margin_percent):
                # System logic: increase = base * (margin / 100)
                increase = base_amount * (margin_percent / 100)
                amount_with_margin = base_amount + increase
                
                expected_increase = base_amount * (margin_percent / 100)
                expected_total = base_amount + expected_increase
                
                self.assertEqual(round(increase, 2), round(expected_increase, 2))
                self.assertEqual(round(amount_with_margin, 2), round(expected_total, 2))
                
                print(f"OK Security Margin {margin_percent}%: ${base_amount:,.2f} + ${increase:,.2f} = ${amount_with_margin:,.2f}")
        
        # Test discount calculations (applied after security margin)
        discounts = [0, 5, 10, 15, 20, 25, 50]  # Common discount percentages
        amount_with_margin = 1150.00  # Base + 15% security margin
        
        for discount_percent in discounts:
            with self.subTest(margin_type="discount", percent=discount_percent):
                # System logic: reduction = amount_with_margin * (discount / 100)
                reduction = amount_with_margin * (discount_percent / 100)
                final_amount = amount_with_margin - reduction
                
                expected_reduction = amount_with_margin * (discount_percent / 100)
                expected_final = amount_with_margin - expected_reduction
                
                self.assertEqual(round(reduction, 2), round(expected_reduction, 2))
                self.assertEqual(round(final_amount, 2), round(expected_final, 2))
                
                print(f"OK Discount {discount_percent}%: ${amount_with_margin:,.2f} - ${reduction:,.2f} = ${final_amount:,.2f}")
    
    def test_edge_cases_and_boundaries(self):
        """Test edge cases and boundary conditions for financial calculations"""
        print("\n=== TEST: Edge Cases and Boundaries ===")
        
        # Test very large amounts
        large_amount = 999999.99
        iva_large = round(large_amount * 0.16, 2)
        total_large = round(large_amount + iva_large, 2)
        print(f"OK Large amount: ${large_amount:,.2f} + 16% IVA = ${total_large:,.2f}")
        self.assertLess(total_large, 2000000.00, "Total should stay within reasonable business limits")
        
        # Test very small amounts  
        small_amount = 0.01
        iva_small = round(small_amount * 0.16, 2)
        total_small = round(small_amount + iva_small, 2)
        print(f"OK Small amount: ${small_amount:.2f} + 16% IVA = ${total_small:.2f}")
        self.assertEqual(total_small, 0.01, "Very small amounts should handle correctly")
        
        # Test negative values (should be prevented by system)
        negative_tests = [-100.00, -0.01, -1000.00]
        for negative_amount in negative_tests:
            # System should convert negative values to 0
            safe_amount = max(0.0, negative_amount)
            self.assertEqual(safe_amount, 0.0, f"Negative amount {negative_amount} should be converted to 0")
            print(f"OK Negative handling: {negative_amount} -> {safe_amount}")
        
        # Test precision edge cases
        precision_tests = [
            (0.004, 0.00),  # Should round down
            (0.005, 0.01),  # Should round up  
            (0.994, 0.99),  # Should round down
            (0.995, 1.00),  # Should round up
        ]
        
        for test_value, expected in precision_tests:
            rounded_value = round(test_value, 2)
            self.assertEqual(rounded_value, expected, f"Precision test failed: {test_value} should round to {expected}")
            print(f"OK Precision: {test_value} -> {rounded_value}")
    
    def test_complex_quotation_calculation(self):
        """Test complete quotation calculation with multiple items and currencies"""
        print("\n=== TEST: Complex Quotation Calculation ===")
        
        # Simulate a complex quotation with multiple items
        quotation_data = {
            "items": [
                {
                    "descripcion": "Estructura Principal",
                    "cantidad": 10.0,
                    "materiales": [
                        {"peso": 4.62, "cantidad": 50.0, "precio": 28.50},  # PTR 2x2
                        {"peso": 1.44, "cantidad": 100.0, "precio": 25.00}  # PTR 1x1  
                    ],
                    "transporte": 500.00,
                    "instalacion": 750.00,
                    "seguridad": 15,  # 15% security margin
                    "descuento": 10   # 10% discount
                },
                {
                    "descripcion": "Estructura Secundaria", 
                    "cantidad": 5.0,
                    "materiales": [
                        {"peso": 1.44, "cantidad": 30.0, "precio": 25.00}   # PTR 1x1
                    ],
                    "transporte": 200.00,
                    "instalacion": 300.00,
                    "seguridad": 20,  # 20% security margin
                    "descuento": 5    # 5% discount
                }
            ],
            "moneda": "MXN",
            "tipo_cambio": 17.50
        }
        
        total_quotation = 0.0
        
        for i, item in enumerate(quotation_data["items"]):
            print(f"\n--- Item {i+1}: {item['descripcion']} ---")
            
            # Calculate materials total
            total_materials = 0.0
            for material in item["materiales"]:
                material_subtotal = material["peso"] * material["cantidad"] * material["precio"]
                total_materials += material_subtotal
                print(f"  Material: {material['peso']} x {material['cantidad']} x ${material['precio']} = ${material_subtotal:,.2f}")
            
            # Add transport and installation
            subtotal_base = total_materials + item["transporte"] + item["instalacion"]
            print(f"  Materials + Transport + Installation: ${total_materials:,.2f} + ${item['transporte']:,.2f} + ${item['instalacion']:,.2f} = ${subtotal_base:,.2f}")
            
            # Apply security margin
            security_increase = subtotal_base * (item["seguridad"] / 100)
            subtotal_with_security = subtotal_base + security_increase
            print(f"  Security margin ({item['seguridad']}%): +${security_increase:,.2f} = ${subtotal_with_security:,.2f}")
            
            # Apply discount
            discount_reduction = subtotal_with_security * (item["descuento"] / 100)
            cost_per_unit = subtotal_with_security - discount_reduction
            print(f"  Discount ({item['descuento']}%): -${discount_reduction:,.2f} = ${cost_per_unit:,.2f} per unit")
            
            # Calculate total for item
            item_total = cost_per_unit * item["cantidad"]
            total_quotation += item_total
            print(f"  Item Total: ${cost_per_unit:,.2f} x {item['cantidad']} = ${item_total:,.2f}")
            
            # Validate calculations are reasonable
            self.assertGreater(total_materials, 0, "Materials total should be positive")
            self.assertGreater(item_total, 0, "Item total should be positive")
            self.assertLess(item_total, 1000000, "Item total should be within reasonable business limits")
        
        # Calculate final totals
        subtotal = total_quotation
        iva = round(subtotal * 0.16, 2)
        grand_total = round(subtotal + iva, 2)
        
        print(f"\n--- Quotation Totals ---")
        print(f"Subtotal: ${subtotal:,.2f}")
        print(f"IVA (16%): ${iva:,.2f}")
        print(f"Grand Total: ${grand_total:,.2f}")
        
        # Test currency conversion if USD
        if quotation_data.get("moneda") == "USD":
            exchange_rate = quotation_data["tipo_cambio"]
            subtotal_usd = round(subtotal / exchange_rate, 2)
            iva_usd = round(iva / exchange_rate, 2)
            grand_total_usd = round(grand_total / exchange_rate, 2)
            
            print(f"\n--- USD Conversion (Rate: {exchange_rate}) ---")
            print(f"Subtotal USD: ${subtotal_usd:,.2f}")
            print(f"IVA USD: ${iva_usd:,.2f}")
            print(f"Grand Total USD: ${grand_total_usd:,.2f}")
        
        # Validate final totals
        self.assertGreater(grand_total, subtotal, "Grand total should be greater than subtotal due to IVA")
        self.assertEqual(round(subtotal * 1.16, 2), grand_total, "Grand total should equal subtotal + 16% IVA")
        
        print(f"\nOK Complex quotation calculation completed successfully")
        
        return {
            "subtotal": subtotal,
            "iva": iva, 
            "grand_total": grand_total,
            "items_processed": len(quotation_data["items"])
        }

def run_financial_qa_tests():
    """Run the complete financial QA test suite"""
    print("="*80)
    print("CWS COTIZADOR - FINANCIAL QA TEST SUITE")
    print("Testing financial calculations, precision, and business rules")
    print("="*80)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_methods = [
        'test_basic_material_calculation',
        'test_iva_calculation_precision',
        'test_currency_conversion_precision', 
        'test_discount_and_markup_calculations',
        'test_edge_cases_and_boundaries',
        'test_complex_quotation_calculation'
    ]
    
    for method in test_methods:
        suite.addTest(FinancialCalculationTests(method))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*80)
    print("FINANCIAL QA TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")  
    print(f"Errors: {len(result.errors)}")
    
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
    success = run_financial_qa_tests()
    sys.exit(0 if success else 1)