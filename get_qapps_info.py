"""
Q Business & Q Apps Information Retrieval Tool

This script retrieves all Q Business applications and Q Apps from your AWS account
and exports the data to a CSV file with comprehensive details.

Features:
- Loads AWS credentials from .env file
- Reads configuration from YAML file
- Lists all Q Business applications
- Retrieves Q Apps details (user count, owner)
- Exports to CSV/JSON with customizable columns
- Handles errors gracefully

Usage:
    python get_qapps_info.py [--config path/to/config.yml]

Date: November 11, 2025
"""

import os
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path

import boto3
import yaml
from botocore.exceptions import ClientError
from dotenv import load_dotenv


class QBusinessInfoRetriever:
    """Retrieve Q Business and Q Apps information from AWS"""
    
    def __init__(self, config_path='./input/config.yml', env_path='./config/.env'):
        """
        Initialize the retriever with configuration from YAML and credentials from .env
        
        Args:
            config_path: Path to YAML configuration file
            env_path: Path to .env file with AWS credentials
        """
        # Load configuration from YAML
        self.config = self._load_config(config_path)
        
        # Load environment variables from .env
        load_dotenv(env_path)
        
        # Get credentials from environment (or use profile)
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_session_token = os.getenv('AWS_SESSION_TOKEN')
        
        # Get region from config or env (config takes precedence)
        self.aws_region = self.config.get('aws', {}).get('region') or os.getenv('AWS_REGION', 'us-east-1')
        self.aws_profile = self.config.get('aws', {}).get('profile') or os.getenv('AWS_PROFILE')
        self.expected_account = self.config.get('aws', {}).get('expected_account_id') or os.getenv('AWS_ACCOUNT_ID')
        
        # Initialize boto3 session
        self.session = self._create_session()
        self.qbusiness_client = None
        self.qapps_client = None
        
        # Logging settings
        self.verbose = self.config.get('logging', {}).get('verbose', True)
        self.show_warnings = self.config.get('logging', {}).get('show_permission_warnings', True)
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if self.verbose if hasattr(self, 'verbose') else True:
                    print(f"✅ Configuration loaded from: {config_path}")
                return config or {}
        except FileNotFoundError:
            print(f"⚠️  Config file not found: {config_path}")
            print(f"   Using default configuration")
            return self._get_default_config()
        except yaml.YAMLError as e:
            print(f"❌ Error parsing YAML config: {e}")
            print(f"   Using default configuration")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Return default configuration"""
        return {
            'aws': {'region': 'us-east-1'},
            'export': {
                'include_empty_apps': True,
                'formats': {'csv': True, 'json': True},
                'filename_pattern': 'qapps_export_{datetime}'
            },
            'retrieval': {
                'max_applications_per_page': 50,
                'max_qapps_per_page': 100
            },
            'output': {'columns': {}},
            'logging': {'level': 'INFO', 'verbose': True, 'show_permission_warnings': True}
        }
        
    def _create_session(self):
        """Create boto3 session with credentials from .env"""
        session_params = {'region_name': self.aws_region}
        
        if self.aws_profile:
            # Use named profile
            session_params['profile_name'] = self.aws_profile
        elif self.aws_access_key and self.aws_secret_key:
            # Use access keys
            session_params['aws_access_key_id'] = self.aws_access_key
            session_params['aws_secret_access_key'] = self.aws_secret_key
            if self.aws_session_token:
                session_params['aws_session_token'] = self.aws_session_token
        
        return boto3.Session(**session_params)
    
    def verify_credentials(self):
        """Verify AWS credentials are valid"""
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            
            if self.verbose:
                print("✅ AWS Credentials Verified")
                print(f"   Account: {identity['Account']}")
                print(f"   User/Role: {identity['Arn'].split('/')[-1]}")
                print(f"   Region: {self.aws_region}\n")
            
            # Verify account matches expected
            if self.expected_account and identity['Account'] != self.expected_account:
                if self.show_warnings:
                    print(f"⚠️  Warning: Connected to account {identity['Account']}, "
                          f"expected {self.expected_account}")
            
            return True
            
        except ClientError as e:
            print(f"❌ Credential verification failed: {e}")
            return False
    
    def list_qbusiness_applications(self):
        """
        List all Q Business applications in the account
        
        Returns:
            List of application dictionaries
        """
        try:
            if not self.qbusiness_client:
                self.qbusiness_client = self.session.client('qbusiness')
            
            if self.verbose:
                print("🔍 Retrieving Q Business applications...\n")
            
            applications = []
            next_token = None
            max_results = self.config.get('retrieval', {}).get('max_applications_per_page', 50)
            
            while True:
                params = {'maxResults': max_results}
                if next_token:
                    params['nextToken'] = next_token
                
                response = self.qbusiness_client.list_applications(**params)
                apps = response.get('applications', [])
                
                for app in apps:
                    # Get detailed info for each application
                    try:
                        detail = self.qbusiness_client.get_application(
                            applicationId=app['applicationId']
                        )
                        applications.append(detail)
                    except ClientError as e:
                        if self.show_warnings:
                            print(f"⚠️  Could not get details for {app['applicationId']}: {e}")
                        applications.append(app)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            if self.verbose:
                print(f"✅ Found {len(applications)} Q Business application(s)\n")
            return applications
            
        except ClientError as e:
            print(f"❌ Error listing Q Business applications: {e}")
            return []
    
    def get_qapps_for_application(self, application_id):
        """
        Get Q Apps library items for a specific Q Business application
        
        Args:
            application_id: Q Business application ID
            
        Returns:
            List of Q Apps with details
        """
        try:
            if not self.qapps_client:
                self.qapps_client = self.session.client('qapps')
            
            if self.verbose:
                print(f"   📱 Retrieving Q Apps for application {application_id}...")
            
            qapps = []
            next_token = None
            max_limit = self.config.get('retrieval', {}).get('max_qapps_per_page', 100)
            
            while True:
                params = {
                    'instanceId': application_id,
                    'limit': max_limit
                }
                if next_token:
                    params['nextToken'] = next_token
                
                response = self.qapps_client.list_library_items(**params)
                items = response.get('libraryItems', [])
                
                # Get detailed info for each Q App
                for item in items:
                    try:
                        detail = self.qapps_client.get_library_item(
                            instanceId=application_id,
                            libraryItemId=item['libraryItemId']
                        )
                        qapps.append(detail)
                    except ClientError as e:
                        error_code = e.response['Error']['Code']
                        if self.show_warnings:
                            print(f"      ⚠️  Could not get details for {item.get('libraryItemId')}: "
                                  f"{error_code}")
                        qapps.append(item)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            if self.verbose:
                print(f"      ✅ Found {len(qapps)} Q App(s)")
            return qapps
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UnauthorizedException':
                if self.show_warnings:
                    print(f"      ℹ️  Q Apps API requires user-level authentication")
            else:
                if self.show_warnings:
                    print(f"      ⚠️  Error: {error_code}")
            return []
    
    def retrieve_all_data(self):
        """
        Retrieve all Q Business applications and Q Apps data
        
        Returns:
            List of dictionaries with comprehensive data
        """
        all_data = []
        include_empty = self.config.get('export', {}).get('include_empty_apps', True)
        
        # Get all Q Business applications
        applications = self.list_qbusiness_applications()
        
        for app in applications:
            app_id = app.get('applicationId', 'N/A')
            app_name = app.get('displayName', app.get('applicationId', 'N/A'))
            
            if self.verbose:
                print(f"\n📊 Processing: {app_name}")
            
            # Try to get Q Apps for this application
            qapps = self.get_qapps_for_application(app_id)
            
            if qapps:
                # Add each Q App as a row
                for qapp in qapps:
                    row = self._create_data_row(app, qapp)
                    all_data.append(row)
            elif include_empty:
                # No Q Apps found, add Q Business app info only
                row = self._create_data_row(app, None)
                all_data.append(row)
        
        return all_data
    
    def _create_data_row(self, app, qapp=None):
        """Create a data row from application and Q App data"""
        row = {
            # Q Business Application Info
            'qbusiness_app_name': app.get('displayName', app.get('applicationId', 'N/A')),
            'qbusiness_app_id': app.get('applicationId', 'N/A'),
            'qbusiness_status': app.get('status', 'N/A'),
            'qbusiness_identity_type': app.get('identityType', 'N/A'),
            'qbusiness_created_at': str(app.get('createdAt', 'N/A')),
            'qbusiness_updated_at': str(app.get('updatedAt', 'N/A')),
            'qbusiness_encryption': app.get('encryptionConfiguration', {}).get('kmsKeyId', 'AWS Managed'),
        }
        
        if qapp:
            # Q App Info
            row.update({
                'qapp_name': qapp.get('title', qapp.get('libraryItemId', 'N/A')),
                'qapp_library_item_id': qapp.get('libraryItemId', 'N/A'),
                'qapp_id': qapp.get('appId', 'N/A'),
                'qapp_version': qapp.get('appVersion', 'N/A'),
                'qapp_status': qapp.get('status', 'N/A'),
                
                # User and Usage Info (PRIMARY REQUIREMENTS)
                'user_count': qapp.get('userCount', 0),
                'owner_created_by': qapp.get('createdBy', 'N/A'),
                'created_at': str(qapp.get('createdAt', 'N/A')),
                
                # Additional Details
                'updated_by': qapp.get('updatedBy', 'N/A'),
                'updated_at': str(qapp.get('updatedAt', 'N/A')),
                'rating_count': qapp.get('ratingCount', 0),
                'is_verified': qapp.get('isVerified', False),
                'is_rated_by_user': qapp.get('isRatedByUser', False),
                'description': qapp.get('description', 'N/A'),
                'categories': ', '.join([cat.get('title', '') for cat in qapp.get('categories', [])]),
            })
        else:
            # No Q Apps - use N/A values
            row.update({
                'qapp_name': 'No Q Apps',
                'qapp_library_item_id': 'N/A',
                'qapp_id': 'N/A',
                'qapp_version': 'N/A',
                'qapp_status': 'N/A',
                'user_count': 0,
                'owner_created_by': 'N/A',
                'created_at': 'N/A',
                'updated_by': 'N/A',
                'updated_at': 'N/A',
                'rating_count': 0,
                'is_verified': False,
                'is_rated_by_user': False,
                'description': 'N/A',
                'categories': 'N/A',
            })
        
        # Add metadata
        row.update({
            'retrieval_timestamp': datetime.now().isoformat(),
            'aws_region': self.aws_region,
            'aws_account': self.expected_account or 'N/A'
        })
        
        return row
    
    def export_to_csv(self, data, filename=None):
        """
        Export data to CSV file
        
        Args:
            data: List of dictionaries with Q Apps data
            filename: Output CSV filename (optional, uses config pattern if not provided)
        """
        if not data:
            print("⚠️  No data to export")
            return
        
        # Ensure output directory exists
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            pattern = self.config.get('export', {}).get('filename_pattern', 'qapps_export_{datetime}')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = pattern.replace('{datetime}', timestamp)
            filename = filename.replace('{date}', datetime.now().strftime('%Y%m%d'))
            filename = filename.replace('{time}', datetime.now().strftime('%H%M%S'))
            filename = filename.replace('{region}', self.aws_region)
            if self.expected_account:
                filename = filename.replace('{account}', self.expected_account)
            filename = f"{filename}.csv"
        
        # Save to output folder
        output_path = output_dir / filename
        
        try:
            # Get enabled columns from config
            column_config = self.config.get('output', {}).get('columns', {})
            
            # Define all possible columns
            all_fieldnames = [
                'qapp_name', 'user_count', 'owner_created_by',
                'qbusiness_app_name', 'qbusiness_app_id', 'qbusiness_status',
                'qbusiness_identity_type', 'qbusiness_created_at', 'qbusiness_updated_at',
                'qbusiness_encryption', 'qapp_library_item_id', 'qapp_id',
                'qapp_version', 'qapp_status', 'created_at', 'updated_by', 'updated_at',
                'rating_count', 'is_verified', 'is_rated_by_user',
                'description', 'categories',
                'retrieval_timestamp', 'aws_region', 'aws_account'
            ]
            
            # Filter columns based on config (if config specifies, otherwise use all)
            if column_config:
                fieldnames = [col for col in all_fieldnames if column_config.get(col, True)]
            else:
                fieldnames = all_fieldnames
            
            # Get CSV encoding from config
            encoding = self.config.get('export', {}).get('csv', {}).get('encoding', 'utf-8')
            include_headers = self.config.get('export', {}).get('csv', {}).get('include_headers', True)
            
            with open(output_path, 'w', newline='', encoding=encoding) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                if include_headers:
                    writer.writeheader()
                writer.writerows(data)
            
            print(f"\n✅ CSV exported to: {output_path}")
            print(f"   Total rows: {len(data)}")
            print(f"   Total columns: {len(fieldnames)}")
            
        except Exception as e:
            print(f"❌ Error exporting to CSV: {e}")
    
    def export_to_json(self, data, filename=None):
        """
        Export data to JSON file (backup format)
        
        Args:
            data: List of dictionaries with Q Apps data
            filename: Output JSON filename (optional)
        """
        if not data:
            return
        
        # Check if JSON export is enabled
        if not self.config.get('export', {}).get('formats', {}).get('json', True):
            return
        
        # Ensure output directory exists
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            pattern = self.config.get('export', {}).get('filename_pattern', 'qapps_export_{datetime}')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = pattern.replace('{datetime}', timestamp)
            filename = filename.replace('{date}', datetime.now().strftime('%Y%m%d'))
            filename = filename.replace('{time}', datetime.now().strftime('%H%M%S'))
            filename = filename.replace('{region}', self.aws_region)
            if self.expected_account:
                filename = filename.replace('{account}', self.expected_account)
            filename = f"{filename}.json"
        
        # Save to output folder
        output_path = output_dir / filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, default=str)
            
            print(f"✅ JSON backup exported to: {output_path}")
            
        except Exception as e:
            print(f"⚠️  Error exporting to JSON: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Retrieve Q Business and Q Apps information from AWS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_qapps_info.py
  python get_qapps_info.py --config input/custom_config.yml
  python get_qapps_info.py --config input/config.yml --env config/.env

For more information, see the README.md file.
        """
    )
    
    parser.add_argument(
        '--config',
        default='./input/config.yml',
        help='Path to YAML configuration file (default: ./input/config.yml)'
    )
    
    parser.add_argument(
        '--env',
        default='./config/.env',
        help='Path to .env file with AWS credentials (default: ./config/.env)'
    )
    
    return parser.parse_args()


def main():
    """Main execution function"""
    # Parse command line arguments
    args = parse_arguments()
    
    print("\n" + "=" * 100)
    print("Q BUSINESS & Q APPS INFORMATION RETRIEVAL TOOL")
    print("=" * 100)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Config: {args.config}")
    print(f"Credentials: {args.env}")
    print("=" * 100 + "\n")
    
    # Initialize retriever
    print("🔧 Initializing...")
    retriever = QBusinessInfoRetriever(config_path=args.config, env_path=args.env)
    
    # Verify credentials
    if not retriever.verify_credentials():
        print("❌ Exiting due to credential issues")
        return
    
    # Retrieve all data
    print("🚀 Starting data retrieval...\n")
    data = retriever.retrieve_all_data()
    
    if not data:
        print("\n⚠️  No data retrieved. Exiting.")
        return
    
    # Export data
    print("\n" + "=" * 100)
    print("📊 EXPORTING DATA")
    print("=" * 100)
    
    # Export to CSV (always enabled)
    retriever.export_to_csv(data)
    
    # Export to JSON (if enabled in config)
    retriever.export_to_json(data)
    
    # Summary
    print("\n" + "=" * 100)
    print("📈 SUMMARY")
    print("=" * 100)
    
    total_apps = len(set(row['qbusiness_app_id'] for row in data if row['qbusiness_app_id'] != 'N/A'))
    total_qapps = sum(1 for row in data if row['qapp_id'] != 'N/A')
    total_users = sum(row.get('user_count', 0) for row in data)
    
    print(f"   Q Business Applications: {total_apps}")
    print(f"   Q Apps Retrieved: {total_qapps}")
    print(f"   Total User Count: {total_users}")
    print(f"   Output Directory: ./output/")
    print("=" * 100)
    
    print("\n✅ Done!\n")


if __name__ == "__main__":
    main()
