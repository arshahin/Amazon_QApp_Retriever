# Q Business & Q Apps Information Retrieval Tool

Retrieve comprehensive information about all Q Business applications and Q Apps in your AWS account and export to CSV.

**Status:** Production Ready ✨  
**Version:** 1.0  
**Last Updated:** November 11, 2025

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [CSV Export Details](#csv-export-details)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Last Execution Summary](#last-execution-summary)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Maintenance](#maintenance)

---

## Features

✅ **YAML configuration support** - Customizable runtime settings  
✅ **Loads credentials from .env file** - Secure credential management  
✅ **Retrieves all Q Business applications** - Complete inventory  
✅ **Attempts to get Q Apps details** - User count, owner, ratings  
✅ **Exports to CSV with 25+ columns** - Comprehensive data export  
✅ **Optional JSON backup** - Additional export format  
✅ **Customizable column output** - Enable/disable specific columns  
✅ **Flexible filename patterns** - Customize output filenames  
✅ **Error handling** - Graceful failure handling  
✅ **Production-ready structure** - Organized folders with git protection  
✅ **Command-line arguments** - Override config paths

---

## Quick Start

```powershell
# 1. Activate virtual environment (if using one)
cd <your_workspace_path>
.\venv\Scripts\Activate.ps1

# 2. Navigate to package directory
cd src\qapp_info_retrival

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
# Copy config/.env.example to config/.env and add your AWS credentials

# 5. Run the script
python get_qapps_info.py
```

**Output:** Files saved to `output/` directory with timestamp (e.g., `output/qapps_export_20251111_213143.csv`)

---

## Project Structure

```
src/qapp_info_retrival/
├── config/                    # AWS credentials
│   ├── .env                   # Active AWS credentials (git-ignored)
│   └── .env.example           # Credential template
├── input/                     # Configuration files
│   ├── config.yml             # Runtime configuration (git-ignored)
│   └── config.example.yml     # Configuration template
├── output/                    # Generated exports (git-ignored)
│   ├── .gitkeep               # Preserves directory
│   ├── qapps_export_*.csv     # CSV exports
│   └── qapps_export_*.json    # JSON exports (optional)
├── get_qapps_info.py          # ⭐ PRODUCTION SCRIPT
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── .gitignore                 # Security protection
```

---

## CSV Export Details

### All Columns (25 total)

#### Required Minimum (3)
- `qapp_name` - Q App name/identifier ✅
- `user_count` - Number of users with access ✅
- `owner_created_by` - App creator/owner ✅

#### Q Business Application (7)
- `qbusiness_app_name` - Q Business application name
- `qbusiness_app_id` - Application ID
- `qbusiness_status` - Application status
- `qbusiness_identity_type` - Authentication type
- `qbusiness_created_at` - When app was created
- `qbusiness_updated_at` - Last update
- `qbusiness_encryption` - Encryption key info

#### Q App Details (8)
- `qapp_library_item_id` - Library item ID
- `qapp_id` - Q App ID
- `qapp_version` - App version number
- `qapp_status` - App status
- `created_at` - Q App creation date
- `updated_by` - Last person to update
- `updated_at` - Last update timestamp
- `description` - App description

#### Usage & Ratings (4)
- `rating_count` - Number of ratings
- `is_verified` - Verification status
- `is_rated_by_user` - If current user rated it
- `categories` - App categories/tags

#### Metadata (3)
- `retrieval_timestamp` - When data was retrieved
- `aws_region` - AWS region
- `aws_account` - AWS account ID

### Sample CSV Output

```csv
qapp_name,user_count,owner_created_by,qbusiness_app_name,qbusiness_app_id,...
My Q App,5,abc123-user-id,my_qbusiness_app,app-id-123...
Another App,3,xyz789-user-id,another_qbusiness_app,app-id-456...
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**

- `boto3>=1.28.0` - AWS SDK for Python
- `python-dotenv>=1.0.0` - Environment variable management
- `pyyaml>=6.0.0` - YAML configuration file support

### 2. Configure Runtime Settings

The tool uses a YAML configuration file for runtime settings. Copy the example and customize:

```bash
cp input/config.example.yml input/config.yml
# Edit input/config.yml to customize settings
```

**Key configuration options:**

- `aws.region` - AWS region (default: us-east-1)
- `aws.profile` - AWS CLI profile name (optional)
- `export.include_empty_apps` - Include apps with no Q Apps (default: true)
- `export.formats` - Enable CSV/JSON export (both enabled by default)
- `export.filename_pattern` - Customize output filename
- `output.columns` - Enable/disable specific columns
- `logging.verbose` - Show detailed progress (default: true)

### 3. Configure AWS Credentials

Edit `config/.env` with your AWS credentials:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token  # Optional, for temporary credentials
AWS_REGION=us-east-1  # Optional, overridden by config.yml if specified
AWS_ACCOUNT_ID=your_account_id  # Optional, for verification
```

> **⚠️ Authentication Method Variations:**  
> The credential setup may vary depending on your AWS authentication configuration:
> - **IAM Users:** Use long-term access keys (not recommended for production)
> - **IAM Identity Center (SSO):** Use temporary session tokens (recommended)
> - **IAM Roles:** Assumed roles may require different credential providers
> - **AWS CLI Profiles:** Can use named profiles instead of environment variables
> 
> **Permission Requirements:**  
> Your IAM user/role must have permissions for:
> - `qbusiness:ListApplications`
> - `qbusiness:GetApplication`
> - `qapps:ListLibraryItems`
> - `qapps:GetLibraryItem` (user-level access may be required)
>
> Consult your AWS administrator if you encounter permission errors.

**How to get credentials (IAM Identity Center example):**

1. Log in to AWS IAM Identity Center
2. Select your role (e.g., PowerUser, Admin)
3. Click "Command line or programmatic access"
4. Copy credentials to `config/.env`

---

## Usage

### Running the Script

**Basic usage:**

```powershell
# From src/qapp_info_retrival directory
python get_qapps_info.py
```

**With custom configuration:**

```powershell
# Use a different config file
python get_qapps_info.py --config input/custom_config.yml

# Specify both config and credentials
python get_qapps_info.py --config input/config.yml --env config/.env
```

**Command-line options:**

- `--config` - Path to YAML configuration file (default: `./input/config.yml`)
- `--env` - Path to .env credentials file (default: `./config/.env`)

### Expected Output

```text
✓ Credentials verified successfully
✓ Found X Q Business applications
✓ Retrieved Y Q Apps
✓ CSV exported to: output/qapps_export_YYYYMMDD_HHMMSS.csv
✓ JSON exported to: output/qapps_export_YYYYMMDD_HHMMSS.json
```

> **Note:** Actual results depend on your Q Business applications and permissions.

### Output Files

The script generates timestamped files in the `output/` directory:

- `qapps_export_YYYYMMDD_HHMMSS.csv` - Main CSV export
- `qapps_export_YYYYMMDD_HHMMSS.json` - JSON backup (if enabled in config)

**Filename customization:**

Edit `input/config.yml` to customize the filename pattern:

```yaml
export:
  filename_pattern: "qapps_export_{datetime}"
  # Available variables: {date}, {time}, {datetime}, {region}, {account}
```

Example outputs:

- `output/qapps_export_20251111_213143.csv`
- `output/qapps_export_20251111_213143.json`

### Using the Data

**Open in Excel:**

```powershell
Start-Process output\qapps_export_20251111_213143.csv
```

**Open in Python/Pandas:**

```python
import pandas as pd
df = pd.read_csv('output/qapps_export_20251111_213143.csv')
print(df[['qapp_name', 'user_count', 'owner_created_by']])
```

**Analysis examples:**

- Sort by `user_count` to find most popular apps
- Filter by `qbusiness_status = 'ACTIVE'`
- Group by `owner_created_by` to see who creates most apps
- Analyze creation dates for adoption trends

---

## Last Execution Summary

This section shows example results from a typical execution. Your results will vary based on your Q Business applications and Q Apps.

### Example Results

**Q Business Applications Found:** 2 (example)

**Export Statistics:**

- Total Q Business Applications: Varies by account
- Total Q Apps Retrieved: Varies by account  
- CSV Columns: 25
- Output Format: CSV + JSON backup

**Files Generated:**

- `output/qapps_export_YYYYMMDD_HHMMSS.csv`
- `output/qapps_export_YYYYMMDD_HHMMSS.json`

### Sample Export Data

The CSV will contain rows for each Q App found in your Q Business applications. Fields include:

- Q App identifiers and names
- User counts and ownership information
- Creation and update timestamps
- Q Business application metadata
- Ratings and verification status

> **Note:** Actual data retrieved depends on your AWS permissions and Q Business configuration.

---

## Known Limitations

### Q Apps API Access

**Issue:** GetLibraryItem API may return `UnauthorizedException`

**Reason:** Q Apps API requires user-level authentication, not just admin/role permissions

**Impact:** May not retrieve full Q App names and descriptions

**What typically works:**

- Library item IDs ✅
- User count ✅
- Owner ID ✅
- Status and timestamps ✅
- Version information ✅

**Workarounds:**

1. Access Q Apps through the AWS web interface
2. Use user-level credentials instead of admin role
3. Manually map library item IDs to friendly names
4. Request user-level AWS access for complete metadata

> **⚠️ Permission Variations:**  
> Results depend heavily on your AWS setup:
> - IAM policies attached to your user/role
> - Identity Center (SSO) permission sets
> - Q Business application access controls
> - Resource-based policies on Q Apps
>
> If you encounter authorization errors, consult your AWS administrator to verify:
> - Required IAM permissions are granted
> - Q Business application access is configured
> - User-level Q Apps permissions (if needed)

### Temporary Credentials

**Issue:** AWS credentials expire (especially with session tokens)

**Solution:** Update `config/.env` file when credentials expire

**Frequency:** Varies by authentication method
- IAM Identity Center: Usually 1-12 hours
- IAM User: Permanent (until rotated)
- Assumed Roles: Configured duration (default 1 hour)

**How to refresh:**

1. Return to your authentication provider (IAM Identity Center, AWS Console, etc.)
2. Generate new temporary credentials
3. Update `config/.env` with new values

---

## Troubleshooting

### "Invalid security token" Error

**Cause:** Your credentials have expired

**Solution:**

1. Get new temporary credentials from IAM Identity Center
2. Update `config/.env` file with new credentials
3. Run the script again

### "Unauthorized" for Q Apps

**Cause:** Q Apps API requires user-level authentication

**Impact:**

- Script will still export Q Business application data
- Q App fields may show library item IDs instead of friendly names
- User count and owner information may be limited

**Solution:** 

- Verify IAM permissions include Q Apps access
- Consider using user credentials instead of service/admin role
- Check with AWS administrator about permission sets and resource policies

> **Authentication & Authorization Notes:**  
> Q Business and Q Apps have different permission models. Your authentication method (IAM user, SSO, assumed role) and authorization policies (IAM policies, permission sets, resource-based policies) significantly affect what data you can retrieve. Always verify with your AWS security team for proper access configuration.

### "No data retrieved"

**Checklist:**

- ✓ Verify AWS credentials are valid and not expired
- ✓ Check region matches where your Q Business apps are deployed
- ✓ Ensure Q Business applications exist in your account
- ✓ Verify network connectivity to AWS endpoints
- ✓ Confirm IAM permissions for Q Business and Q Apps APIs
- ✓ Check if using correct AWS account (if multi-account setup)

### "Module not found" Error

**Solution:**

```powershell
pip install -r requirements.txt
```

---

## Security

### Critical Security Rules

⚠️ **IMPORTANT:** Never commit `config/.env` to version control

**Protected by .gitignore:**

```gitignore
# AWS Credentials
config/.env

# Output Files  
output/*.csv
output/*.json

# Python
__pycache__/
*.pyc
venv/
```

### Best Practices

- ✅ Keep credentials in `config/.env` (git-ignored)
- ✅ Use `.env.example` template for setup instructions
- ✅ Rotate credentials regularly
- ✅ Use temporary session tokens when possible
- ✅ Restrict CSV file access (may contain sensitive data)
- ✅ Clean up old output files periodically

### Data Handling

- CSV files contain AWS account information
- Owner IDs are user identifiers (UUIDs)
- Library item IDs are unique resource identifiers
- Treat exports as internal-only documents

---

## Maintenance

### Regular Tasks

**Weekly:**

- Run script to get updated Q Apps data
- Review new applications and changes
- Monitor user adoption trends

**Monthly:**

- Clean up old exports in `output/` directory
- Archive historical data if needed
- Review and optimize queries

**As Needed:**

- Update credentials in `config/.env` when expired
- Refresh Python dependencies (`pip install --upgrade -r requirements.txt`)
- Check for AWS API updates

**Quarterly:**

- Review archived scripts in `archive/` folder
- Consider permanent deletion of very old scripts
- Update documentation with new findings

### Future Enhancements

**Immediate Actions:**

1. Verify credentials in `config/.env` are current
2. Run script to generate fresh export
3. Review output CSV for completeness

**Potential Improvements:**

1. **User-level Access:** Request Q Apps user authentication for complete metadata
2. **Scheduling:** Set up automated runs to track Q Apps changes over time
3. **Reporting:** Integrate CSV exports with PowerBI/Tableau/QuickSight
4. **Mapping:** Create library_item_id to friendly name mapping table
5. **Monitoring:** Track credential expiration and automate refresh
6. **Notifications:** Add email alerts on completion or errors
7. **Incremental Updates:** Track changes between runs
8. **Data Validation:** Add quality checks and validation rules
9. **Multi-Account Support:** Extend to work across multiple AWS accounts
10. **Advanced Filtering:** Add command-line options for filtering results

### Production Readiness Checklist

- [x] Main script (`get_qapps_info.py`) tested and working
- [x] Dependencies documented in `requirements.txt`
- [x] Credentials securely stored in `config/.env`
- [x] Credential template (`config/.env.example`) provided
- [x] Output directory (`output/`) created and configured
- [x] Git protection (`.gitignore`) implemented
- [x] Documentation complete (this README)
- [x] Old files archived with explanations
- [x] Folder structure logical and maintainable
- [x] All required CSV columns present
- [x] Error handling implemented
- [x] Security best practices followed

---

## Support

For issues or questions:

- Check [Troubleshooting](#troubleshooting) section above
- Review AWS IAM permissions for your role
- Check CloudWatch logs for API errors
- Verify network connectivity to AWS endpoints
- Contact AWS support for API-specific issues

---

## Summary

The Q Apps information retrieval package is production-ready with:

- ✅ Clean, logical folder structure
- ✅ Secure credential management
- ✅ Comprehensive documentation
- ✅ Git protection for sensitive files
- ✅ Archived development history
- ✅ Tested and working code
- ✅ All required CSV columns (qapp_name, user_count, owner_created_by)
- ✅ 25 total columns with comprehensive metadata
- ✅ JSON backup exports
- ✅ Graceful error handling

**Status:** Ready for regular use and team collaboration  
**Created:** November 11, 2025  
**Version:** 1.0
