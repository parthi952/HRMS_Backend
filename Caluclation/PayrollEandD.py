def calculate_salary(base_salary, earnings, deductions):
    """
    Dynamically calculates payroll components based on base salary, 
    earnings, and deductions.
    """
    total_earnings = 0.0
    total_deductions = 0.0
    earnings_breakdown = []
    deductions_breakdown = []

    # Handle Earnings
    for e in earnings:
        amount = 0.0
        # Use getattr or . access depending on object type (ORM vs Dict)
        e_type = getattr(e, 'type', None)
        e_value = float(getattr(e, 'value', 0) or 0)
        e_name = getattr(e, 'name', 'Unknown')

        if e_type == "percentage":
            amount = round(base_salary * (e_value / 100), 2)
        else:
            amount = round(e_value, 2)
        
        total_earnings += amount
        earnings_breakdown.append({
            "name": e_name,
            "type": e_type,
            "value": e_value,
            "amount": amount
        })

    # Handle Deductions
    for d in deductions:
        amount = 0.0
        d_type = getattr(d, 'type', None)
        d_value = float(getattr(d, 'value', 0) or 0)
        d_name = getattr(d, 'name', 'Unknown')

        if d_type == "percentage":
            amount = round(base_salary * (d_value / 100), 2)
        else:
            amount = round(d_value, 2)
        
        total_deductions += amount
        deductions_breakdown.append({
            "name": d_name,
            "type": d_type,
            "value": d_value,
            "amount": amount
        })

    # Final calculations
    gross_salary = round(base_salary + total_earnings, 2)
    net_salary = round(gross_salary - total_deductions, 2)

    return {
        "base_salary": round(base_salary, 2),
        "gross_salary": gross_salary,
        "total_earnings": round(total_earnings, 2),
        "total_deductions": round(total_deductions, 2),
        "net_salary": net_salary,
        "earnings_breakdown": earnings_breakdown,
        "deductions_breakdown": deductions_breakdown
    }