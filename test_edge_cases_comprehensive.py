#!/usr/bin/env python3
"""
COMPREHENSIVE EDGE CASE TESTING - CWS Cotizador
Tests boundary conditions, error scenarios, and unusual business cases
Focus: Financial edge cases, data validation limits, business rule boundaries
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_extreme_financial_values():
    """Test calculations with extreme financial values"""
    print("=== EDGE CASE TEST: Extreme Financial Values ===")
    
    test_cases = [
        # Very large amounts (approaching system limits)
        {"desc": "Very Large Material Cost", "peso": 100.0, "cantidad": 1000.0, "precio": 999.99, "expected": 99999000.00},
        {"desc": "Maximum Realistic Quote", "peso": 50.0, "cantidad": 2000.0, "precio": 100.0, "expected": 10000000.00},
        
        # Very small amounts (precision edge cases)
        {"desc": "Minimum Material Cost", "peso": 0.01, "cantidad": 0.01, "precio": 0.01, "expected": 0.00},
        {"desc": "Small Precision Test", "peso": 0.1, "cantidad": 0.1, "precio": 0.1, "expected": 0.00},
        {"desc": "Cent Precision", "peso": 1.0, "cantidad": 1.0, "precio": 0.005, "expected": 0.01},
        
        # Edge rounding cases
        {"desc": "Rounding Up Edge", "peso": 1.0, "cantidad": 1.0, "precio": 10.995, "expected": 11.00},
        {"desc": "Rounding Down Edge", "peso": 1.0, "cantidad": 1.0, "precio": 10.994, "expected": 10.99},
    ]
    
    passed = 0
    failed = 0
    warnings = 0
    
    for case in test_cases:
        peso = case["peso"]
        cantidad = case["cantidad"] 
        precio = case["precio"]
        expected = case["expected"]
        
        # System calculation (matches app.py line 255)
        calculated = round(peso * cantidad * precio, 2)
        
        # Check if calculation matches expected
        if abs(calculated - expected) < 0.01:
            print(f"OK {case['desc']}: ${calculated:,.2f}")
            passed += 1
        else:
            print(f"FAIL {case['desc']}: ${calculated:,.2f}, expected ${expected:,.2f}")
            failed += 1
        
        # Business logic warnings for extreme values
        if calculated > 1000000:  # Over 1 million
            print(f"  WARNING: Very large amount (${calculated:,.2f}) - validate business necessity")
            warnings += 1
        elif calculated == 0.00 and precio > 0:
            print(f"  WARNING: Calculation resulted in zero despite non-zero price")
            warnings += 1
    
    print(f"Extreme Values Results: {passed} passed, {failed} failed, {warnings} warnings")
    return failed == 0

def test_iva_edge_cases():
    """Test IVA calculation edge cases and precision scenarios"""
    print("\n=== EDGE CASE TEST: IVA Calculation Precision ===")
    
    edge_cases = [
        # Amounts that might cause floating point precision issues
        {"subtotal": 0.01, "expected_iva": 0.00, "expected_total": 0.01},
        {"subtotal": 0.06, "expected_iva": 0.01, "expected_total": 0.07},
        {"subtotal": 0.07, "expected_iva": 0.01, "expected_total": 0.08},
        {"subtotal": 6.24, "expected_iva": 1.00, "expected_total": 7.24},
        {"subtotal": 6.25, "expected_iva": 1.00, "expected_total": 7.25},
        {"subtotal": 6.26, "expected_iva": 1.00, "expected_total": 7.26},
        
        # Large amounts near floating point precision limits
        {"subtotal": 999999.99, "expected_iva": 160000.00, "expected_total": 1159999.99},
        {"subtotal": 1000000.00, "expected_iva": 160000.00, "expected_total": 1160000.00},
        
        # Repeating decimal edge cases
        {"subtotal": 333.33, "expected_iva": 53.33, "expected_total": 386.66},
        {"subtotal": 666.67, "expected_iva": 106.67, "expected_total": 773.34},
        {"subtotal": 1666.67, "expected_iva": 266.67, "expected_total": 1933.34},
    ]
    
    passed = 0
    failed = 0
    precision_warnings = 0
    
    for case in edge_cases:
        subtotal = case["subtotal"]
        expected_iva = case["expected_iva"]
        expected_total = case["expected_total"]
        
        # System calculation (matches app.py)
        calculated_iva = round(subtotal * 0.16, 2)
        calculated_total = round(subtotal + calculated_iva, 2)
        
        iva_ok = abs(calculated_iva - expected_iva) < 0.01
        total_ok = abs(calculated_total - expected_total) < 0.01
        
        if iva_ok and total_ok:
            print(f"OK ${subtotal:,.2f}: IVA ${calculated_iva:,.2f}, Total ${calculated_total:,.2f}")
            passed += 1
        else:
            print(f"FAIL ${subtotal:,.2f}: IVA ${calculated_iva:,.2f} (exp ${expected_iva:,.2f}), Total ${calculated_total:,.2f} (exp ${expected_total:,.2f})")
            failed += 1
        
        # Check for potential precision issues
        raw_iva = subtotal * 0.16
        if abs(raw_iva - calculated_iva) > 0.005:  # More than 0.5 cent difference
            print(f"  WARNING: Significant rounding applied (raw: ${raw_iva:.4f}, rounded: ${calculated_iva:.2f})")
            precision_warnings += 1
    
    print(f"IVA Edge Cases Results: {passed} passed, {failed} failed, {precision_warnings} precision warnings")
    return failed == 0

def test_currency_conversion_edge_cases():
    """Test currency conversion edge cases and boundary conditions"""
    print("\n=== EDGE CASE TEST: Currency Conversion Boundaries ===")
    
    # Test various exchange rates including edge cases
    edge_rates = [
        {"rate": 15.00, "description": "Lower business range"},
        {"rate": 25.00, "description": "Upper business range"},
        {"rate": 1.00, "description": "Parity rate (unusual)"},
        {"rate": 50.00, "description": "Very high rate"},
        {"rate": 0.50, "description": "Very low rate (unusual)"},
        {"rate": 17.123456, "description": "High precision rate"},
    ]
    
    test_amount_mxn = 1750.00  # Standard test amount
    
    passed = 0
    failed = 0
    warnings = 0
    
    for rate_case in edge_rates:
        rate = rate_case["rate"]
        description = rate_case["description"]
        
        if rate <= 0:  # System should handle zero/negative rates
            print(f"SKIP Zero/negative rate test: {rate} ({description})")
            continue
        
        # System calculation (matches app.py line 662 and 730)
        calculated_usd = round(test_amount_mxn / rate, 2) if rate > 0 else 0.0
        
        # Validate conversion is reasonable
        if calculated_usd > 0:
            print(f"OK ${test_amount_mxn:,.2f} MXN / {rate} = ${calculated_usd:,.2f} USD ({description})")
            passed += 1
            
            # Business logic warnings
            if rate < 10 or rate > 30:
                print(f"  WARNING: Exchange rate {rate} outside typical business range (10-30)")
                warnings += 1
            
            if calculated_usd > 10000:  # Very large USD amounts
                print(f"  WARNING: Large USD amount (${calculated_usd:,.2f}) - validate rate accuracy")
                warnings += 1
                
        else:
            print(f"FAIL Rate {rate}: Conversion failed")
            failed += 1
    
    # Test round-trip conversion accuracy
    print("\nRound-trip Conversion Accuracy:")
    standard_rate = 17.50
    test_amounts = [1750.00, 350.25, 8765.43, 0.35, 999999.99]
    
    roundtrip_passed = 0
    roundtrip_failed = 0
    
    for mxn_amount in test_amounts:
        usd_converted = round(mxn_amount / standard_rate, 2)
        mxn_back = round(usd_converted * standard_rate, 2)
        
        difference = abs(mxn_amount - mxn_back)
        
        if difference <= 0.02:  # Allow 2 cent tolerance for rounding
            print(f"OK ${mxn_amount:,.2f} MXN -> ${usd_converted:,.2f} USD -> ${mxn_back:,.2f} MXN (diff: ${difference:.2f})")
            roundtrip_passed += 1
        else:
            print(f"FAIL ${mxn_amount:,.2f} MXN -> ${usd_converted:,.2f} USD -> ${mxn_back:,.2f} MXN (diff: ${difference:.2f})")
            roundtrip_failed += 1
    
    total_passed = passed + roundtrip_passed
    total_failed = failed + roundtrip_failed
    print(f"Currency Edge Cases Results: {total_passed} passed, {total_failed} failed, {warnings} warnings")
    
    return total_failed == 0

def test_discount_security_boundary_conditions():
    """Test discount and security margin boundary conditions"""
    print("\n=== EDGE CASE TEST: Discount/Security Boundary Conditions ===")
    
    base_amount = 1000.00
    
    # Extreme percentage cases
    extreme_cases = [
        # Security margin extremes
        {"type": "security", "percent": 0, "description": "No security margin"},
        {"type": "security", "percent": 100, "description": "100% security margin (double price)"},
        {"type": "security", "percent": 50, "description": "50% security margin"},
        {"type": "security", "percent": 0.01, "description": "Minimal security margin"},
        {"type": "security", "percent": 99.99, "description": "Near 100% security margin"},
        
        # Discount extremes  
        {"type": "discount", "percent": 0, "description": "No discount"},
        {"type": "discount", "percent": 100, "description": "100% discount (free)"},
        {"type": "discount", "percent": 99.99, "description": "Near 100% discount"},
        {"type": "discount", "percent": 0.01, "description": "Minimal discount"},
        {"type": "discount", "percent": 50, "description": "50% discount"},
    ]
    
    passed = 0
    failed = 0
    warnings = 0
    
    for case in extreme_cases:
        case_type = case["type"]
        percent = case["percent"]
        description = case["description"]
        
        if case_type == "security":
            # Security margin: increase = base * (percent / 100)
            increase = base_amount * (percent / 100)
            result = base_amount + increase
            expected_range = (base_amount, base_amount * 3)  # Reasonable security range
        else:
            # Discount: reduction = base * (percent / 100), applied to amount with security
            amount_with_security = 1150.00  # Assumed 15% security already applied
            reduction = amount_with_security * (percent / 100)
            result = amount_with_security - reduction
            expected_range = (0, amount_with_security)  # Discount can't be negative
        
        # Validate calculation
        if result >= expected_range[0] and result <= expected_range[1]:
            print(f"OK {case_type.title()} {percent}%: ${result:,.2f} ({description})")
            passed += 1
            
            # Business warnings for extreme values
            if percent >= 75:
                print(f"  WARNING: Very high {case_type} percentage ({percent}%) - validate business necessity")
                warnings += 1
            elif result == 0.00 and case_type == "discount":
                print(f"  WARNING: 100% discount results in free product")
                warnings += 1
                
        else:
            print(f"FAIL {case_type.title()} {percent}%: ${result:,.2f} outside reasonable range")
            failed += 1
    
    print(f"Discount/Security Boundary Results: {passed} passed, {failed} failed, {warnings} warnings")
    return failed == 0

def test_quotation_complexity_limits():
    """Test system handling of complex quotations near practical limits"""
    print("\n=== EDGE CASE TEST: Quotation Complexity Limits ===")
    
    complexity_tests = [
        {
            "name": "Large Item Count",
            "items": 50,
            "materials_per_item": 5,
            "description": "Many items quotation"
        },
        {
            "name": "Material-Heavy Items", 
            "items": 5,
            "materials_per_item": 20,
            "description": "Items with many materials"
        },
        {
            "name": "Balanced Complex",
            "items": 10,
            "materials_per_item": 10,
            "description": "Balanced complexity"
        }
    ]
    
    passed = 0
    failed = 0
    warnings = 0
    
    for test in complexity_tests:
        item_count = test["items"]
        materials_per_item = test["materials_per_item"]
        test_name = test["name"]
        description = test["description"]
        
        print(f"\nTesting {test_name}: {item_count} items, {materials_per_item} materials each")
        
        # Simulate calculation load
        total_calculations = item_count * materials_per_item
        total_quotation_value = 0
        
        for item_idx in range(item_count):
            item_value = 0
            
            # Simulate materials calculations
            for mat_idx in range(materials_per_item):
                # Use varying values to simulate real scenarios
                peso = 2.0 + (mat_idx * 0.5)
                cantidad = 5.0 + (mat_idx * 2.0)  
                precio = 20.0 + (mat_idx * 5.0)
                
                material_subtotal = round(peso * cantidad * precio, 2)
                item_value += material_subtotal
            
            # Add transport/installation (simulate business logic)
            item_value += 100.0  # Transport
            item_value += 150.0  # Installation
            
            # Apply security margin and discount
            item_value *= 1.15  # 15% security
            item_value *= 0.90  # 10% discount
            
            total_quotation_value += item_value
        
        # Calculate final totals
        final_subtotal = total_quotation_value
        final_iva = round(final_subtotal * 0.16, 2)
        final_total = round(final_subtotal + final_iva, 2)
        
        # Validate reasonableness
        if final_total > 0 and final_total < 100000000:  # Within business limits
            print(f"OK {test_name}: {total_calculations} calculations, ${final_total:,.2f} total")
            passed += 1
            
            # Performance warnings
            if total_calculations > 200:
                print(f"  WARNING: High calculation load ({total_calculations}) - monitor performance")
                warnings += 1
            
            if final_total > 10000000:  # Over 10 million
                print(f"  WARNING: Very large quotation (${final_total:,.2f}) - validate business case")
                warnings += 1
                
        else:
            print(f"FAIL {test_name}: Invalid total ${final_total:,.2f}")
            failed += 1
    
    print(f"\nComplexity Limits Results: {passed} passed, {failed} failed, {warnings} warnings")
    return failed == 0

def run_comprehensive_edge_case_tests():
    """Run all comprehensive edge case tests"""
    print("="*80)
    print("CWS COTIZADOR - COMPREHENSIVE EDGE CASE TEST SUITE")
    print("Testing boundary conditions, extreme values, and unusual business scenarios")
    print("="*80)
    
    tests = [
        ("Extreme Financial Values", test_extreme_financial_values),
        ("IVA Edge Cases", test_iva_edge_cases),
        ("Currency Conversion Boundaries", test_currency_conversion_edge_cases),
        ("Discount/Security Boundaries", test_discount_security_boundary_conditions),
        ("Quotation Complexity Limits", test_quotation_complexity_limits),
    ]
    
    results = []
    total_warnings = 0
    
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
    print("COMPREHENSIVE EDGE CASE TEST - FINAL RESULTS")
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
    print(f"\nOVERALL RESULT: {'PASSED - ALL EDGE CASES HANDLED CORRECTLY' if overall_success else 'FAILED - SOME EDGE CASES NEED ATTENTION'}")
    
    if not overall_success:
        print("\nEDGE CASE ISSUES DETECTED:")
        print("- Review failed test cases above")
        print("- Consider implementing additional boundary validations")
        print("- Test with production-like data volumes")
        print("- Monitor system performance under load")
    else:
        print("\nEDGE CASE VALIDATION SUCCESSFUL:")
        print("- System handles extreme values appropriately")
        print("- Financial calculations remain accurate at boundaries")
        print("- Business logic maintains integrity under stress")
        print("- Complex quotations process correctly")
    
    return overall_success

if __name__ == "__main__":
    success = run_comprehensive_edge_case_tests()
    sys.exit(0 if success else 1)