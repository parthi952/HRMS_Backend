def mailTemplate(email , raw_password , role , emp_id):
    # Determine portal access link based on role
    role_lower = str(role).lower().strip()
    if role_lower == "employee":
        portal_name = "Employee Self Service Portal"
        portal_link = "https://hrm.tibostech.in/hrm-emp/login"  # Employee hub
    else:
        portal_name = "Admin & Management Console"
        portal_link = "https://hrm.tibostech.in/hrm-tlm/login"  # Admin/Manager selection hub

    html=f"""
   <!DOCTYPE html>

<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HRMS Portal Access</title>
</head>

<body style="margin:0; padding:0; background-color:#f4f6f9; font-family:Arial, sans-serif;">


<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9; padding:30px 15px;">
    <tr>
        <td align="center">

            <table width="100%" cellpadding="0" cellspacing="0" 
                style="max-width:600px; background:#ffffff; border-radius:14px; overflow:hidden; box-shadow:0 4px 18px rgba(0,0,0,0.08);">

                <!-- Header -->
                <tr>
                    <td align="center" 
                        style="background:linear-gradient(135deg,#2563eb,#1e40af); padding:35px 20px; color:#ffffff;">
                        
                        <h1 style="margin:0; font-size:28px;">🏢 HRMS Portal</h1>
                        <p style="margin-top:10px; font-size:15px; opacity:0.9;">
                            Employee Access Credentials
                        </p>
                    </td>
                </tr>

                <!-- Content -->
                <tr>
                    <td style="padding:35px 30px; color:#333333;">

                        <p style="font-size:16px; margin-top:0;">
                            Hello,
                        </p>

                        <p style="font-size:15px; line-height:1.7; color:#555555;">
                            Your account has been successfully created. 
                            Below are your login credentials for accessing the HRMS portal.
                        </p>

                        <!-- Credentials Box -->
                        <table width="100%" cellpadding="0" cellspacing="0" 
                            style="margin-top:25px; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden;">

                            <tr>
                                <td style="padding:14px; background:#f8fafc; font-weight:bold; width:35%;">
                                    📧 Email
                                </td>
                                <td style="padding:14px;">
                                    {email}
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:14px; background:#f8fafc; font-weight:bold;">
                                    🔑 Password
                                </td>
                                <td style="padding:14px; color:#dc2626; font-family:monospace; font-size:15px;">
                                    {raw_password}
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:14px; background:#f8fafc; font-weight:bold;">
                                    👤 Role
                                </td>
                                <td style="padding:14px; text-transform:capitalize;">
                                    {role}
                                </td>
                            </tr>

                            <tr>
                                <td style="padding:14px; background:#f8fafc; font-weight:bold;">
                                    🪪 Employee ID
                                </td>
                                <td style="padding:14px;">
                                    {emp_id}
                                </td>
                            </tr>

                        </table>

                        <!-- Button -->
                        <div style="text-align:center; margin:35px 0 25px;">
                            
                            <p style="margin-bottom:15px; font-size:14px; color:#6b7280;">
                                Click the button below to access your portal
                            </p>

                            <a href="{portal_link}" 
                               style="display:inline-block;
                                      background:#2563eb;
                                      color:#ffffff;
                                      text-decoration:none;
                                      padding:14px 30px;
                                      border-radius:8px;
                                      font-size:15px;
                                      font-weight:bold;
                                      box-shadow:0 4px 10px rgba(37,99,235,0.3);">
                                🚀 {portal_name}
                            </a>
                        </div>
                        <!-- Footer -->
                        <p style="margin-top:35px; font-size:13px; color:#9ca3af; line-height:1.6;">
                            This is an automatically generated email. Please do not reply to this message.
                        </p>

                    </td>
                </tr>

                <!-- Footer Bottom -->
                <tr>
                    <td align="center" 
                        style="padding:18px; background:#f9fafb; color:#9ca3af; font-size:12px;">
                        © 2026 HRMS Portal. All rights reserved.
                    </td>
                </tr>

            </table>

        </td>
    </tr>
</table>


</body>
</html>

    """
    return html