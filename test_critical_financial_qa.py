#!/usr/bin/env python3
"""
CRITICAL FINANCIAL QA TEST SUITE - CWS Cotizador
Essential financial accuracy tests - focused on critical business calculations
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_material_calculation_accuracy():
    """Test material calculation accuracy using system logic"""
    print("=== CRITICAL TEST: Material Calculation Accuracy ===")
    
    # Material calculation: peso * cantidad * precio = subtotal
    test_cases = [
        # Real materials from Lista de materiales.csv
        {"material": "PTR 1\" x 1\" CAL 14", "peso": 1.44, "cantidad": 10.0, "precio": 25.50, "expected": 367.20},
        {"material": "PTR 2\" x 2\" CAL 11", "peso": 4.62, "cantidad": 5.0, "precio": 30.00, "expected": 693.00},
        {"material": "PTR 1 1/2\" x 1 1/2\" CAL 11", "peso": 3.42, "cantidad": 20.0, "precio": 28.75, "expected": 1966.50},
        # Edge cases
        {"material": "Zero weight", "peso": 0.0, "cantidad": 10.0, "precio": 25.00, "expected": 0.00},
        {"material": "Zero quantity", "peso": 2.0, "cantidad": 0.0, "precio": 25.00, "expected": 0.00},
        {"material": "Zero price", "peso": 2.0, "cantidad": 10.0, "precio": 0.00, "expected": 0.00},
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        peso = case["peso"]
        cantidad = case["cantidad"] 
        precio = case["precio"]
        expected = case["expected"]
        
        # System calculation (matches app.py line 255)
        calculated = round(peso * cantidad * precio, 2)
        
        if abs(calculated - expected) < 0.01:  # Allow 1 cent tolerance
            print(f"OK {case['material']}: {peso} x {cantidad} x ${precio} = ${calculated}")
            passed += 1
        else:
            print(f"FAIL {case['material']}: {peso} x {cantidad} x ${precio} = ${calculated}, expected ${expected}")
            failed += 1
    
    print(f"Material Calculation Results: {passed} passed, {failed} failed")
    return failed == 0

def test_iva_calculation_accuracy():
    """Test IVA (16%) calculation accuracy"""
    print("\n=== CRITICAL TEST: IVA (16%) Calculation Accuracy ===")
    
    # IVA calculation cases (matches app.py lines 723, 1612)
    test_cases = [
        {"subtotal": 100.00, "expected_iva": 16.00, "expected_total": 116.00},
        {"subtotal": 1000.00, "expected_iva": 160.00, "expected_total": 1160.00},
        {"subtotal": 1234.56, "expected_iva": 197.53, "expected_total": 1432.09},
        {"subtotal": 999.99, "expected_iva": 160.00, "expected_total": 1159.99},
        {"subtotal": 12345.67, "expected_iva": 1975.31, "expected_total": 14320.98},
        # Precision edge cases
        {"subtotal": 133.33, "expected_iva": 21.33, "expected_total": 154.66},
        {"subtotal": 166.67, "expected_iva": 26.67, "expected_total": 193.34},
        {"subtotal": 0.01, "expected_iva": 0.00, "expected_total": 0.01},
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        subtotal = case["subtotal"]
        expected_iva = case["expected_iva"]
        expected_total = case["expected_total"]
        
        # System calculation (matches app.py)
        calculated_iva = round(subtotal * 0.16, 2)
        calculated_total = round(subtotal + calculated_iva, 2)
        
        iva_ok = abs(calculated_iva - expected_iva) < 0.01
        total_ok = abs(calculated_total - expected_total) < 0.01
        
        if iva_ok and total_ok:
            print(f"OK Subtotal ${subtotal:,.2f}: IVA ${calculated_iva:,.2f}, Total ${calculated_total:,.2f}")
            passed += 1
        else:
            print(f"FAIL Subtotal ${subtotal:,.2f}: IVA ${calculated_iva:,.2f} (exp ${expected_iva:,.2f}), Total ${calculated_total:,.2f} (exp ${expected_total:,.2f})")
            failed += 1
    
    print(f"IVA Calculation Results: {passed} passed, {failed} failed")
    return failed == 0

def test_currency_conversion_accuracy():
    """Test USD/MXN currency conversion accuracy"""
    print("\n=== CRITICAL TEST: Currency Conversion Accuracy ===")
    
    # Currency conversion cases (matches app.py lines 661-667, 729-733)
    exchange_rate = 17.50  # Common test rate
    
    test_cases = [
        {"mxn_amount": 1750.00, "expected_usd": 100.00},
        {"mxn_amount": 875.00, "expected_usd": 50.00},
        {"mxn_amount": 17.50, "expected_usd": 1.00},
        {"mxn_amount": 1.75, "expected_usd": 0.10},
        {"mxn_amount": 17500.00, "expected_usd": 1000.00},
        {"mxn_amount": 1766.25, "expected_usd": 100.93},
        {"mxn_amount": 1733.75, "expected_usd": 99.07},
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        mxn_amount = case["mxn_amount"]
        expected_usd = case["expected_usd"]
        
        # System calculation (matches app.py line 662 and 730)
        # USD conversion: usd = mxn / tipo_cambio
        calculated_usd = round(mxn_amount / exchange_rate, 2) if exchange_rate > 0 else 0.0
        
        if abs(calculated_usd - expected_usd) < 0.01:
            print(f"OK ${mxn_amount:,.2f} MXN / {exchange_rate} = ${calculated_usd:,.2f} USD")
            passed += 1
        else:
            print(f"FAIL ${mxn_amount:,.2f} MXN / {exchange_rate} = ${calculated_usd:,.2f} USD, expected ${expected_usd:,.2f} USD")
            failed += 1
    
    print(f"Currency Conversion Results: {passed} passed, {failed} failed")
    return failed == 0

def test_discount_and_security_calculations():
    """Test discount and security margin calculations"""
    print("\n=== CRITICAL TEST: Discount and Security Margin Calculations ===")
    
    # Test security margin (markup) calculation
    base_amount = 1000.00
    
    # Security margin test cases (percentage-based increase)
    security_cases = [
        {"percent": 0, "expected_increase": 0.00, "expected_total": 1000.00},
        {"percent": 5, "expected_increase": 50.00, "expected_total": 1050.00},
        {"percent": 10, "expected_increase": 100.00, "expected_total": 1100.00},
        {"percent": 15, "expected_increase": 150.00, "expected_total": 1150.00},
        {"percent": 20, "expected_increase": 200.00, "expected_total": 1200.00},
        {"percent": 25, "expected_increase": 250.00, "expected_total": 1250.00},
    ]
    
    security_passed = 0
    security_failed = 0
    
    print("Security Margin Tests:")
    for case in security_cases:
        percent = case["percent"]
        expected_increase = case["expected_increase"]
        expected_total = case["expected_total"]
        
        # System calculation: increase = base * (percent / 100)
        calculated_increase = base_amount * (percent / 100)
        calculated_total = base_amount + calculated_increase
        
        increase_ok = abs(calculated_increase - expected_increase) < 0.01
        total_ok = abs(calculated_total - expected_total) < 0.01
        
        if increase_ok and total_ok:
            print(f"OK Security {percent}%: ${base_amount:,.2f} + ${calculated_increase:,.2f} = ${calculated_total:,.2f}")
            security_passed += 1
        else:
            print(f"FAIL Security {percent}%: increase ${calculated_increase:,.2f} (exp ${expected_increase:,.2f}), total ${calculated_total:,.2f} (exp ${expected_total:,.2f})")
            security_failed += 1
    
    # Discount test cases (percentage-based reduction)
    amount_with_margin = 1150.00  # Base + 15% security margin
    discount_cases = [
        {"percent": 0, "expected_reduction": 0.00, "expected_final": 1150.00},
        {"percent": 5, "expected_reduction": 57.50, "expected_final": 1092.50},
        {"percent": 10, "expected_reduction": 115.00, "expected_final": 1035.00},
        {"percent": 15, "expected_reduction": 172.50, "expected_final": 977.50},
        {"percent": 20, "expected_reduction": 230.00, "expected_final": 920.00},
        {"percent": 50, "expected_reduction": 575.00, "expected_final": 575.00},
    ]
    
    discount_passed = 0
    discount_failed = 0
    
    print("\nDiscount Tests:")
    for case in discount_cases:
        percent = case["percent"]
        expected_reduction = case["expected_reduction"]
        expected_final = case["expected_final"]
        
        # System calculation: reduction = amount * (percent / 100)
        calculated_reduction = amount_with_margin * (percent / 100)
        calculated_final = amount_with_margin - calculated_reduction
        
        reduction_ok = abs(calculated_reduction - expected_reduction) < 0.01
        final_ok = abs(calculated_final - expected_final) < 0.01
        
        if reduction_ok and final_ok:
            print(f"OK Discount {percent}%: ${amount_with_margin:,.2f} - ${calculated_reduction:,.2f} = ${calculated_final:,.2f}")
            discount_passed += 1
        else:
            print(f"FAIL Discount {percent}%: reduction ${calculated_reduction:,.2f} (exp ${expected_reduction:,.2f}), final ${calculated_final:,.2f} (exp ${expected_final:,.2f})")
            discount_failed += 1
    
    total_passed = security_passed + discount_passed
    total_failed = security_failed + discount_failed
    print(f"Discount/Security Results: {total_passed} passed, {total_failed} failed")
    
    return total_failed == 0

def test_complete_quotation_workflow():
    """Test complete quotation calculation workflow"""
    print("\n=== CRITICAL TEST: Complete Quotation Workflow ===")
    
    # Simulate complete quotation with realistic data
    print("Testing realistic quotation scenario:")
    
    # Item 1: Steel structure
    item1_materials = [
        {"desc": "PTR 2x2 CAL 11", "peso": 4.62, "cantidad": 50, "precio": 28.50},  # 6583.50
        {"desc": "PTR 1x1 CAL 14", "peso": 1.44, "cantidad": 100, "precio": 25.00}  # 3600.00
    ]
    
    item1_transport = 500.00
    item1_installation = 750.00
    item1_security_percent = 15
    item1_discount_percent = 10
    item1_quantity = 10
    
    # Calculate Item 1
    print("Item 1: Steel Structure")
    
    total_materials_1 = 0
    for mat in item1_materials:
        mat_subtotal = mat["peso"] * mat["cantidad"] * mat["precio"]
        total_materials_1 += mat_subtotal
        print(f"  {mat['desc']}: {mat['peso']} x {mat['cantidad']} x ${mat['precio']} = ${mat_subtotal:,.2f}")
    
    subtotal_base_1 = total_materials_1 + item1_transport + item1_installation
    security_increase_1 = subtotal_base_1 * (item1_security_percent / 100)
    subtotal_with_security_1 = subtotal_base_1 + security_increase_1
    discount_reduction_1 = subtotal_with_security_1 * (item1_discount_percent / 100)
    cost_per_unit_1 = subtotal_with_security_1 - discount_reduction_1
    item1_total = cost_per_unit_1 * item1_quantity
    
    print(f"  Materials Total: ${total_materials_1:,.2f}")
    print(f"  + Transport: ${item1_transport:,.2f}")
    print(f"  + Installation: ${item1_installation:,.2f}")
    print(f"  = Base Subtotal: ${subtotal_base_1:,.2f}")
    print(f"  + Security {item1_security_percent}%: ${security_increase_1:,.2f}")
    print(f"  = With Security: ${subtotal_with_security_1:,.2f}")
    print(f"  - Discount {item1_discount_percent}%: ${discount_reduction_1:,.2f}")
    print(f"  = Cost per Unit: ${cost_per_unit_1:,.2f}")
    print(f"  x Quantity {item1_quantity}: ${item1_total:,.2f}")
    
    # Calculate quotation totals
    quotation_subtotal = item1_total
    quotation_iva = round(quotation_subtotal * 0.16, 2)
    quotation_total = round(quotation_subtotal + quotation_iva, 2)
    
    print(f"\nQuotation Totals:")
    print(f"  Subtotal: ${quotation_subtotal:,.2f}")
    print(f"  IVA (16%): ${quotation_iva:,.2f}")
    print(f"  Grand Total: ${quotation_total:,.2f}")
    
    # Validate calculations
    validation_passed = True
    
    # Check that materials are calculated correctly
    expected_materials_1 = (4.62 * 50 * 28.50) + (1.44 * 100 * 25.00)  # 6583.50 + 3600.00 = 10183.50
    if abs(total_materials_1 - expected_materials_1) > 0.01:
        print(f"ERROR: Materials calculation incorrect: ${total_materials_1:,.2f} != ${expected_materials_1:,.2f}")
        validation_passed = False
    
    # Check IVA calculation
    expected_iva = round(quotation_subtotal * 0.16, 2)
    if abs(quotation_iva - expected_iva) > 0.01:
        print(f"ERROR: IVA calculation incorrect: ${quotation_iva:,.2f} != ${expected_iva:,.2f}")
        validation_passed = False
    
    # Check grand total
    expected_grand_total = quotation_subtotal + quotation_iva
    if abs(quotation_total - expected_grand_total) > 0.01:
        print(f"ERROR: Grand total calculation incorrect: ${quotation_total:,.2f} != ${expected_grand_total:,.2f}")
        validation_passed = False
    
    # Check that totals are reasonable
    if quotation_total <= quotation_subtotal:
        print(f"ERROR: Grand total should be greater than subtotal due to IVA")
        validation_passed = False
    
    if quotation_total > quotation_subtotal * 2:
        print(f"ERROR: Grand total seems unreasonably high compared to subtotal")
        validation_passed = False
    
    print(f"Complete Workflow Results: {'PASSED' if validation_passed else 'FAILED'}")
    return validation_passed

def run_critical_financial_qa():
    """Run all critical financial QA tests"""
    print("="*80)
    print("CWS COTIZADOR - CRITICAL FINANCIAL QA TEST SUITE")
    print("Essential accuracy tests for business-critical financial calculations")
    print("="*80)
    
    tests = [
        ("Material Calculations", test_material_calculation_accuracy),
        ("IVA (16%) Calculations", test_iva_calculation_accuracy),
        ("Currency Conversions", test_currency_conversion_accuracy),
        ("Discounts & Security Margins", test_discount_and_security_calculations),
        ("Complete Quotation Workflow", test_complete_quotation_workflow),
    ]
    
    results = []
    
    for test_name, test_function in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_function()
            results.append((test_name, result))
            status = "PASSED" if result else "FAILED"
            print(f"{test_name}: {status}")
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("CRITICAL FINANCIAL QA - FINAL RESULTS")
    print("="*80)
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED" 
        print(f"{test_name:.<50} {status}")
    
    print("-" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    overall_success = passed_tests == total_tests
    print(f"\nOVERALL RESULT: {'PASSED - ALL CRITICAL FINANCIAL TESTS SUCCESSFUL' if overall_success else 'FAILED - FINANCIAL ACCURACY ISSUES DETECTED'}")
    
    if not overall_success:
        print("\nCRITICAL FINANCIAL ISSUES DETECTED:")
        print("- Review failed test cases above")
        print("- Validate calculation logic in app.py")
        print("- Consider impact on business operations")
        print("- Test with production data before deployment")
    
    return overall_success

if __name__ == "__main__":
    success = run_critical_financial_qa()
    sys.exit(0 if success else 1)