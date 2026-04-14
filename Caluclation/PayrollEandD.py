def calculate_salary(base_salary, earnings, deductions):
    total_earnings = 0
    total_deductions = 0

    for e in earnings:
        if e.type == "percentage":
            total_earnings += base_salary * float(e.value) / 100
        else:
            total_earnings += float(e.value)

    for d in deductions:
        if d.type == "percentage":
            total_deductions += base_salary * float(d.value) / 100
        else:
            total_deductions += float(d.value)

    final_salary = base_salary + total_earnings - total_deductions

    return {
        "earnings": total_earnings,
        "deductions": total_deductions,
        "net_salary": final_salary
    }