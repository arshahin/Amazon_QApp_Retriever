"""
Q Business Global Export Tool - Enhanced with User Details

This script retrieves comprehensive information about Q Business applications including:
- Q Apps details (user count, owner, ratings) WITH USER EMAILS
- Application configuration (identity, security, settings)
- Data sources, retrievers, and plugins
- Chat controls (blocked phrases, topics, guardrails)
- User information (usernames, emails, display names) from IAM Identity Center
- All combined in a single CSV/JSON export

New in Enhanced Version:
- Maps user UUIDs to actual usernames and email addresses
- Adds creator and updater details for each Q App
- Uses IAM Identity Center (identitystore) API for user lookups
- Caches user lookups to minimize API calls

Features:
- Complete Q Business application inventory
- Q Apps with usage metrics AND user details
- Full configuration details
- Chat controls and topic configurations
- Single unified export file with 70 columns

Usage:
    python get_qbusiness_global_enhanced.py [--config path/to/config.yml] [--env path/to/.env]

Date: January 12, 2026
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


class QBusinessGlobalExporterEnhanced:
    """Export complete Q Business application information including Q Apps and configurations with user details"""
    
    def __init__(self, config_path='./input/config.yml', env_path='./config/.env'):
        """Initialize the exporter with configuration"""
        self.config = self._load_config(config_path)
        load_dotenv(env_path)
        
        # AWS settings
        self.aws_region = self.config.get('aws', {}).get('region') or os.getenv('AWS_REGION', 'us-east-1')
        self.aws_profile = self.config.get('aws', {}).get('profile') or os.getenv('AWS_PROFILE')
        self.expected_account = self.config.get('aws', {}).get('expected_account_id') or os.getenv('AWS_ACCOUNT_ID')
        
        # Initialize boto3
        self.session = self._create_session()
        self.qbusiness_client = None
        self.qapps_client = None
        self.identitystore_client = None
        self.sso_admin_client = None
        
        # Cache for user lookups and identity store
        self.user_cache = {}
        self.identity_store_id = None
        
        self.verbose = True
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError):
            return {'aws': {'region': 'us-east-1'}}
    
    def _create_session(self):
        """Create boto3 session"""
        session_params = {'region_name': self.aws_region}
        if self.aws_profile:
            session_params['profile_name'] = self.aws_profile
        return boto3.Session(**session_params)
    
    def verify_credentials(self):
        """Verify AWS credentials"""
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            
            print("✅ AWS Credentials Verified")
            print(f"   Account: {identity['Account']}")
            print(f"   User/Role: {identity['Arn'].split('/')[-1]}")
            print(f"   Region: {self.aws_region}\n")
            return True
        except ClientError as e:
            print(f"❌ Credential verification failed: {e}")
            return False
    
    def get_identity_store_id(self, identity_center_arn):
        """Extract Identity Store ID from Identity Center ARN"""
        try:
            if not self.sso_admin_client:
                self.sso_admin_client = self.session.client('sso-admin')
            
            # List SSO instances to find the Identity Store ID
            response = self.sso_admin_client.list_instances()
            if response.get('Instances'):
                # Usually there's only one instance per account
                identity_store_id = response['Instances'][0]['IdentityStoreId']
                if self.verbose:
                    print(f"   ✅ Found Identity Store ID: {identity_store_id}")
                return identity_store_id
            else:
                if self.verbose:
                    print("   ⚠️  No IAM Identity Center instances found")
                return None
        except ClientError as e:
            if self.verbose:
                print(f"   ⚠️  Could not retrieve Identity Store ID: {e}")
            return None
    
    def get_user_details(self, identity_store_id, user_id):
        """Get user details from Identity Store"""
        # Check cache first
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        # Skip if no identity store or invalid user_id
        if not identity_store_id or user_id == 'N/A':
            user_info = {
                'username': user_id,
                'email': 'N/A',
                'display_name': 'N/A'
            }
            self.user_cache[user_id] = user_info
            return user_info
        
        try:
            if not self.identitystore_client:
                self.identitystore_client = self.session.client('identitystore')
            
            response = self.identitystore_client.describe_user(
                IdentityStoreId=identity_store_id,
                UserId=user_id
            )
            
            # Extract relevant information
            user_info = {
                'username': response.get('UserName', 'N/A'),
                'email': self._extract_email(response),
                'display_name': response.get('DisplayName', 'N/A')
            }
            
            # Cache the result
            self.user_cache[user_id] = user_info
            return user_info
            
        except ClientError as e:
            # Return placeholder on error
            user_info = {
                'username': user_id,
                'email': 'N/A',
                'display_name': 'N/A'
            }
            self.user_cache[user_id] = user_info
            return user_info
    
    def _extract_email(self, user_response):
        """Extract email from user response"""
        emails = user_response.get('Emails', [])
        if emails:
            # Get primary email or first email
            for email in emails:
                if email.get('Primary', False):
                    return email.get('Value', 'N/A')
            return emails[0].get('Value', 'N/A')
        return 'N/A'
    
    def list_applications(self):
        """Get all Q Business applications with details"""
        try:
            if not self.qbusiness_client:
                self.qbusiness_client = self.session.client('qbusiness')
            
            print("🔍 Retrieving Q Business applications...\n")
            
            applications = []
            next_token = None
            
            while True:
                params = {'maxResults': 50}
                if next_token:
                    params['nextToken'] = next_token
                
                response = self.qbusiness_client.list_applications(**params)
                apps = response.get('applications', [])
                
                for app in apps:
                    try:
                        detail = self.qbusiness_client.get_application(
                            applicationId=app['applicationId']
                        )
                        applications.append(detail)
                    except ClientError as e:
                        print(f"⚠️  Could not get details for {app['applicationId']}: {e}")
                        applications.append(app)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            print(f"✅ Found {len(applications)} Q Business application(s)\n")
            return applications
        except ClientError as e:
            print(f"❌ Error listing applications: {e}")
            return []
    
    def get_qapps(self, application_id):
        """Get Q Apps for an application"""
        try:
            if not self.qapps_client:
                self.qapps_client = self.session.client('qapps')
            
            qapps = []
            next_token = None
            
            while True:
                params = {
                    'instanceId': application_id,
                    'limit': 100
                }
                if next_token:
                    params['nextToken'] = next_token
                
                response = self.qapps_client.list_library_items(**params)
                items = response.get('libraryItems', [])
                
                # Note: list_library_items does not return Q App title/name
                # GetQApp and ListQApps APIs require owner permissions (UnauthorizedException)
                # We use libraryItemId as identifier instead
                for item in items:
                    qapps.append(item)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return qapps
        except ClientError:
            return []
    
    def get_data_sources(self, application_id, index_id):
        """Get data sources"""
        try:
            data_sources = []
            next_token = None
            
            while True:
                params = {
                    'applicationId': application_id,
                    'indexId': index_id,
                    'maxResults': 10
                }
                if next_token:
                    params['nextToken'] = next_token
                
                response = self.qbusiness_client.list_data_sources(**params)
                sources = response.get('dataSources', [])
                
                for source in sources:
                    try:
                        detail = self.qbusiness_client.get_data_source(
                            applicationId=application_id,
                            indexId=index_id,
                            dataSourceId=source['dataSourceId']
                        )
                        data_sources.append(detail)
                    except ClientError:
                        data_sources.append(source)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return data_sources
        except ClientError:
            return []
    
    def get_retrievers(self, application_id):
        """Get retrievers"""
        try:
            retrievers = []
            next_token = None
            
            while True:
                params = {
                    'applicationId': application_id,
                    'maxResults': 50
                }
                if next_token:
                    params['nextToken'] = next_token
                
                response = self.qbusiness_client.list_retrievers(**params)
                ret_list = response.get('retrievers', [])
                
                for retriever in ret_list:
                    try:
                        detail = self.qbusiness_client.get_retriever(
                            applicationId=application_id,
                            retrieverId=retriever['retrieverId']
                        )
                        retrievers.append(detail)
                    except ClientError:
                        retrievers.append(retriever)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return retrievers
        except ClientError:
            return []
    
    def get_plugins(self, application_id):
        """Get plugins"""
        try:
            plugins = []
            next_token = None
            
            while True:
                params = {
                    'applicationId': application_id,
                    'maxResults': 50
                }
                if next_token:
                    params['nextToken'] = next_token
                
                response = self.qbusiness_client.list_plugins(**params)
                plugin_list = response.get('plugins', [])
                
                for plugin in plugin_list:
                    try:
                        detail = self.qbusiness_client.get_plugin(
                            applicationId=application_id,
                            pluginId=plugin['pluginId']
                        )
                        plugins.append(detail)
                    except ClientError:
                        plugins.append(plugin)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return plugins
        except ClientError:
            return []
    
    def get_chat_controls(self, application_id):
        """Get chat controls configuration"""
        try:
            response = self.qbusiness_client.get_chat_controls_configuration(
                applicationId=application_id,
                maxResults=50
            )
            return response
        except ClientError:
            return {}
    
    def export_all_data(self):
        """Export complete Q Business data including Q Apps and configurations with user details"""
        all_data = []
        include_empty = self.config.get('export', {}).get('include_empty_apps', True)
        
        # Get all applications
        applications = self.list_applications()
        
        for app in applications:
            app_id = app.get('applicationId', 'N/A')
            app_name = app.get('displayName', app_id)
            
            print(f"📊 Processing: {app_name}")
            
            # Get Identity Store ID if using IAM IDC (only once)
            if not self.identity_store_id:
                identity_type = app.get('identityType')
                if identity_type == 'AWS_IAM_IDC':
                    identity_center_arn = app.get('identityCenterApplicationArn')
                    if identity_center_arn:
                        self.identity_store_id = self.get_identity_store_id(identity_center_arn)
            
            # Get index ID
            index_id = None
            try:
                indices = self.qbusiness_client.list_indices(
                    applicationId=app_id,
                    maxResults=10
                )
                if indices.get('indices'):
                    index_id = indices['indices'][0]['indexId']
            except ClientError:
                pass
            
            # Get Q Apps
            print(f"   📱 Retrieving Q Apps...")
            qapps = self.get_qapps(app_id)
            print(f"      ✅ Found {len(qapps)} Q App(s)")
            
            # Get data sources
            data_sources = []
            if index_id:
                print(f"   📁 Retrieving data sources...")
                data_sources = self.get_data_sources(app_id, index_id)
                print(f"      ✅ Found {len(data_sources)} data source(s)")
            
            # Get retrievers
            print(f"   🔍 Retrieving retrievers...")
            retrievers = self.get_retrievers(app_id)
            print(f"      ✅ Found {len(retrievers)} retriever(s)")
            
            # Get plugins
            print(f"   🔌 Retrieving plugins...")
            plugins = self.get_plugins(app_id)
            print(f"      ✅ Found {len(plugins)} plugin(s)")
            
            # Get chat controls
            print(f"   💬 Retrieving chat controls...")
            chat_controls = self.get_chat_controls(app_id)
            print(f"      ✅ Chat controls retrieved")
            
            # Create rows
            if qapps:
                for qapp in qapps:
                    row = self._create_global_row(app, qapp, data_sources, retrievers, plugins, index_id, chat_controls)
                    all_data.append(row)
            elif include_empty:
                row = self._create_global_row(app, None, data_sources, retrievers, plugins, index_id, chat_controls)
                all_data.append(row)
            
            print()
        
        return all_data
    
    def _create_global_row(self, app, qapp, data_sources, retrievers, plugins, index_id, chat_controls):
        """Create comprehensive data row with user details"""
        
        # Extract app configurations
        attachments = app.get('attachmentsConfiguration', {})
        auto_sub = app.get('autoSubscriptionConfiguration', {})
        personalization = app.get('personalizationConfiguration', {})
        qapps_config = app.get('qAppsConfiguration', {})
        quicksight_config = app.get('quickSightConfiguration', {})
        
        # Extract chat controls
        blocked_phrases_config = chat_controls.get('blockedPhrases', {}) if chat_controls else {}
        creator_mode = chat_controls.get('creatorModeConfiguration', {}) if chat_controls else {}
        hallucination_reduction = chat_controls.get('hallucinationReductionConfiguration', {}) if chat_controls else {}
        orchestration = chat_controls.get('orchestrationConfiguration', {}) if chat_controls else {}
        topic_configs = chat_controls.get('topicConfigurations', []) if chat_controls else []
        
        # Get user details for creator and updater
        creator_id = qapp.get('createdBy', 'N/A') if qapp else 'N/A'
        updater_id = qapp.get('updatedBy', 'N/A') if qapp else 'N/A'
        
        creator_info = self.get_user_details(self.identity_store_id, creator_id)
        updater_info = self.get_user_details(self.identity_store_id, updater_id)
        
        row = {
            # ===== Q APP INFORMATION (Primary) =====
            # Note: Q App title not accessible via API - using libraryItemId as fallback
            'qapp_name': f"Q App {qapp.get('libraryItemId', 'Unknown')}" if qapp else 'No Q Apps',
            'qapp_id': qapp.get('appId', 'N/A') if qapp else 'N/A',
            'qapp_library_item_id': qapp.get('libraryItemId', 'N/A') if qapp else 'N/A',
            'qapp_version': qapp.get('appVersion', 'N/A') if qapp else 'N/A',
            'qapp_status': qapp.get('status', 'N/A') if qapp else 'N/A',
            'qapp_user_count': qapp.get('userCount', 0) if qapp else 0,
            
            # ===== Q APP CREATOR DETAILS (ENHANCED) =====
            'qapp_creator_user_id': creator_id,
            'qapp_creator_username': creator_info['username'],
            'qapp_creator_email': creator_info['email'],
            'qapp_creator_display_name': creator_info['display_name'],
            'qapp_created_at': str(qapp.get('createdAt', 'N/A')) if qapp else 'N/A',
            
            # ===== Q APP UPDATER DETAILS (ENHANCED) =====
            'qapp_updater_user_id': updater_id,
            'qapp_updater_username': updater_info['username'],
            'qapp_updater_email': updater_info['email'],
            'qapp_updated_at': str(qapp.get('updatedAt', 'N/A')) if qapp else 'N/A',
            
            # ===== Q APP ADDITIONAL METADATA =====
            'qapp_rating_count': qapp.get('ratingCount', 0) if qapp else 0,
            'qapp_is_verified': qapp.get('isVerified', False) if qapp else False,
            'qapp_is_rated_by_user': qapp.get('isRatedByUser', False) if qapp else False,
            'qapp_description': qapp.get('description', 'N/A') if qapp else 'N/A',
            'qapp_categories': ', '.join([cat.get('title', '') for cat in qapp.get('categories', [])]) if qapp else 'N/A',
            
            # ===== APPLICATION BASIC INFO =====
            'app_name': app.get('displayName', 'N/A'),
            'app_id': app.get('applicationId', 'N/A'),
            'app_arn': app.get('applicationArn', 'N/A'),
            'app_description': app.get('description', 'N/A'),
            'app_status': app.get('status', 'N/A'),
            'app_created_at': str(app.get('createdAt', 'N/A')),
            'app_updated_at': str(app.get('updatedAt', 'N/A')),
            
            # ===== IDENTITY & SECURITY =====
            'identity_type': app.get('identityType', 'N/A'),
            'identity_center_arn': app.get('identityCenterApplicationArn', 'N/A'),
            'identity_store_id': self.identity_store_id or 'N/A',
            'iam_identity_provider_arn': app.get('iamIdentityProviderArn', 'N/A'),
            'client_ids_for_oidc': ', '.join(app.get('clientIdsForOIDC', [])),
            'role_arn': app.get('roleArn', 'N/A'),
            'encryption_kms_key': app.get('encryptionConfiguration', {}).get('kmsKeyId', 'AWS Managed'),
            
            # ===== APPLICATION CONFIGURATION =====
            'attachments_mode': attachments.get('attachmentsControlMode', 'N/A'),
            'auto_subscribe': auto_sub.get('autoSubscribe', 'N/A'),
            'auto_subscribe_default': auto_sub.get('defaultSubscriptionType', 'N/A'),
            'personalization_mode': personalization.get('personalizationControlMode', 'N/A'),
            'qapps_mode': qapps_config.get('qAppsControlMode', 'N/A'),
            'quicksight_namespace': quicksight_config.get('clientNamespace', 'N/A'),
            
            # ===== CHAT CONTROLS - BLOCKED PHRASES =====
            'blocked_phrases_count': len(blocked_phrases_config.get('blockedPhrases', [])),
            'blocked_phrases': '; '.join(blocked_phrases_config.get('blockedPhrases', [])),
            'blocked_phrases_system_message': blocked_phrases_config.get('systemMessageOverride', 'N/A'),
            
            # ===== CHAT CONTROLS - BEHAVIOR =====
            'creator_mode_control': creator_mode.get('creatorModeControl', 'N/A'),
            'hallucination_reduction_control': hallucination_reduction.get('hallucinationReductionControl', 'N/A'),
            'orchestration_control': orchestration.get('control', 'N/A'),
            'response_scope': chat_controls.get('responseScope', 'N/A') if chat_controls else 'N/A',
            
            # ===== CHAT CONTROLS - TOPICS =====
            'topic_count': len(topic_configs),
            'topic_names': ', '.join([t.get('name', 'N/A') for t in topic_configs]),
            'topic_descriptions': ' | '.join([f"{t.get('name', 'N/A')}: {t.get('description', 'N/A')}" for t in topic_configs]),
            
            # ===== ERROR DETAILS =====
            'error_code': app.get('error', {}).get('errorCode', 'N/A'),
            'error_message': app.get('error', {}).get('errorMessage', 'N/A'),
            
            # ===== INDEX =====
            'index_id': index_id or 'N/A',
            
            # ===== DATA SOURCES =====
            'data_source_count': len(data_sources),
            'data_source_ids': ', '.join([ds.get('dataSourceId', 'N/A') for ds in data_sources]),
            'data_source_types': ', '.join([ds.get('type', 'N/A') for ds in data_sources]),
            'data_source_names': ', '.join([ds.get('displayName', 'N/A') for ds in data_sources]),
            'data_source_statuses': ', '.join([ds.get('status', 'N/A') for ds in data_sources]),
            
            # ===== RETRIEVERS =====
            'retriever_count': len(retrievers),
            'retriever_ids': ', '.join([r.get('retrieverId', 'N/A') for r in retrievers]),
            'retriever_types': ', '.join([r.get('type', 'N/A') for r in retrievers]),
            'retriever_statuses': ', '.join([r.get('status', 'N/A') for r in retrievers]),
            
            # ===== PLUGINS =====
            'plugin_count': len(plugins),
            'plugin_ids': ', '.join([p.get('pluginId', 'N/A') for p in plugins]),
            'plugin_types': ', '.join([p.get('type', 'N/A') for p in plugins]),
            'plugin_statuses': ', '.join([p.get('status', 'N/A') for p in plugins]),
            
            # ===== METADATA =====
            'export_timestamp': datetime.now().isoformat(),
            'aws_region': self.aws_region,
            'aws_account': self.expected_account or 'N/A',
        }
        
        return row
    
    def export_to_csv(self, data, filename=None):
        """Export to CSV"""
        if not data:
            print("⚠️  No data to export")
            return
        
        # Use src/qapp_info_retrival/output directory
        script_dir = Path(__file__).parent
        output_dir = script_dir / 'output'
        output_dir.mkdir(exist_ok=True)
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qbusiness_global_enhanced_{timestamp}.csv"
        
        output_path = output_dir / filename
        
        try:
            fieldnames = list(data[0].keys())
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            print(f"\n✅ CSV exported to: {output_path}")
            print(f"   Total rows: {len(data)}")
            print(f"   Total columns: {len(fieldnames)}")
            
        except Exception as e:
            print(f"❌ Error exporting CSV: {e}")
    
    def export_to_json(self, data, filename=None):
        """Export to JSON"""
        if not data:
            return
        
        # Use src/qapp_info_retrival/output directory
        script_dir = Path(__file__).parent
        output_dir = script_dir / 'output'
        output_dir.mkdir(exist_ok=True)
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qbusiness_global_enhanced_{timestamp}.json"
        
        output_path = output_dir / filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ JSON exported to: {output_path}")
            
        except Exception as e:
            print(f"❌ Error exporting JSON: {e}")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Export complete Q Business application information with user details (ENHANCED VERSION)'
    )
    parser.add_argument('--config', default='./input/config.yml', help='Path to config YAML')
    parser.add_argument('--env', default='./config/.env', help='Path to .env file')
    
    args = parser.parse_args()
    
    # Header
    print("=" * 100)
    print("Q BUSINESS GLOBAL EXPORT TOOL - ENHANCED WITH USER DETAILS")
    print("=" * 100)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Config: {args.config}")
    print(f"Credentials: {args.env}")
    print("=" * 100)
    print()
    
    # Initialize
    print("🔧 Initializing...")
    exporter = QBusinessGlobalExporterEnhanced(args.config, args.env)
    
    # Verify credentials
    if not exporter.verify_credentials():
        print("❌ Exiting due to credential issues")
        return
    
    print("🚀 Starting global data export with user details...\n")
    
    # Export all data
    data = exporter.export_all_data()
    
    if data:
        print("=" * 100)
        print("📊 EXPORTING DATA")
        print("=" * 100)
        print()
        
        # Export
        exporter.export_to_csv(data)
        exporter.export_to_json(data)
        
        # User summary
        print("\n" + "=" * 100)
        print("👥 USER SUMMARY")
        print("=" * 100)
        unique_creators = set(d['qapp_creator_email'] for d in data if d['qapp_creator_email'] != 'N/A')
        print(f"   Unique Q App Creators: {len(unique_creators)}")
        for email in sorted(unique_creators):
            creator_apps = [d for d in data if d['qapp_creator_email'] == email]
            print(f"   - {email}: {len(creator_apps)} Q App(s)")
        
        print("\n" + "=" * 100)
        print("📈 SUMMARY")
        print("=" * 100)
        print(f"   Total Records: {len(data)}")
        print(f"   Q Business Applications: {len(set([d['app_id'] for d in data]))}")
        print(f"   Q Apps Found: {sum(1 for d in data if d['qapp_id'] != 'N/A')}")
        print(f"   Output Directory: ./output/")
        print("=" * 100)
        print("\n✅ Done!")
    else:
        print("⚠️  No data found to export")


if __name__ == "__main__":
    main()
