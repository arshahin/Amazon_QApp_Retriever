"""
Q Business Application Configuration Export Tool

This script retrieves detailed configuration for all Q Business applications 
including data sources, retrievers, plugins, and other settings.

Features:
- Exports Q Business app configurations
- Retrieves data source details
- Retrieves retriever settings
- Retrieves plugin configurations
- Exports to CSV/JSON format

Usage:
    python get_qbusiness_config.py [--config path/to/config.yml] [--env path/to/.env]

Date: December 4, 2025
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


class QBusinessConfigExporter:
    """Export detailed Q Business application configurations"""
    
    def __init__(self, config_path='./input/config.yml', env_path='./config/.env'):
        """
        Initialize the exporter with configuration
        
        Args:
            config_path: Path to YAML configuration file
            env_path: Path to .env file with AWS credentials
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Load credentials
        load_dotenv(env_path)
        
        # Get AWS settings
        self.aws_region = self.config.get('aws', {}).get('region') or os.getenv('AWS_REGION', 'us-east-1')
        self.aws_profile = self.config.get('aws', {}).get('profile') or os.getenv('AWS_PROFILE')
        
        # Initialize boto3 session
        self.session = self._create_session()
        self.qbusiness_client = None
        
        self.verbose = True
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config or {}
        except FileNotFoundError:
            return {'aws': {'region': 'us-east-1'}}
    
    def _create_session(self):
        """Create boto3 session with credentials"""
        session_params = {'region_name': self.aws_region}
        
        if self.aws_profile:
            session_params['profile_name'] = self.aws_profile
        
        return boto3.Session(**session_params)
    
    def verify_credentials(self):
        """Verify AWS credentials are valid"""
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
    
    def list_applications(self):
        """Get all Q Business applications"""
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
    
    def get_data_sources(self, application_id, index_id):
        """Get data sources for an application"""
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
                    except ClientError as e:
                        print(f"      ⚠️  Could not get data source details: {e}")
                        data_sources.append(source)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return data_sources
            
        except ClientError as e:
            print(f"      ⚠️  Error listing data sources: {e}")
            return []
    
    def get_retrievers(self, application_id):
        """Get retrievers for an application"""
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
                    except ClientError as e:
                        print(f"      ⚠️  Could not get retriever details: {e}")
                        retrievers.append(retriever)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return retrievers
            
        except ClientError as e:
            print(f"      ⚠️  Error listing retrievers: {e}")
            return []
    
    def get_plugins(self, application_id):
        """Get plugins for an application"""
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
                    except ClientError as e:
                        print(f"      ⚠️  Could not get plugin details: {e}")
                        plugins.append(plugin)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return plugins
            
        except ClientError as e:
            print(f"      ⚠️  Error listing plugins: {e}")
            return []
    
    def get_chat_controls(self, application_id):
        """Get chat controls configuration for an application"""
        try:
            response = self.qbusiness_client.get_chat_controls_configuration(
                applicationId=application_id,
                maxResults=50
            )
            return response
        except ClientError as e:
            print(f"      ⚠️  Error getting chat controls: {e}")
            return {}
    
    def export_all_configurations(self):
        """Export all Q Business application configurations"""
        
        all_configs = []
        
        # Get all applications
        applications = self.list_applications()
        
        for app in applications:
            app_id = app.get('applicationId', 'N/A')
            app_name = app.get('displayName', app_id)
            
            print(f"📊 Processing: {app_name}")
            
            # Get indexes (needed for data sources)
            index_id = None
            try:
                indices = self.qbusiness_client.list_indices(
                    applicationId=app_id,
                    maxResults=10
                )
                if indices.get('indices'):
                    index_id = indices['indices'][0]['indexId']
            except ClientError as e:
                print(f"   ⚠️  Could not list indices: {e}")
            
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
            
            # Create configuration row
            config_row = self._create_config_row(app, data_sources, retrievers, plugins, index_id, chat_controls)
            all_configs.append(config_row)
            print()
        
        return all_configs
    
    def _create_config_row(self, app, data_sources, retrievers, plugins, index_id, chat_controls=None):
        """Create a configuration data row"""
        
        # Extract configuration details
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
        
        row = {
            # Basic Info
            'app_name': app.get('displayName', 'N/A'),
            'app_id': app.get('applicationId', 'N/A'),
            'app_arn': app.get('applicationArn', 'N/A'),
            'description': app.get('description', 'N/A'),
            'status': app.get('status', 'N/A'),
            'created_at': str(app.get('createdAt', 'N/A')),
            'updated_at': str(app.get('updatedAt', 'N/A')),
            
            # Identity & Security
            'identity_type': app.get('identityType', 'N/A'),
            'identity_center_arn': app.get('identityCenterApplicationArn', 'N/A'),
            'iam_identity_provider_arn': app.get('iamIdentityProviderArn', 'N/A'),
            'client_ids_for_oidc': ', '.join(app.get('clientIdsForOIDC', [])),
            'role_arn': app.get('roleArn', 'N/A'),
            'encryption_kms_key': app.get('encryptionConfiguration', {}).get('kmsKeyId', 'AWS Managed'),
            
            # Configuration Settings - Application Level
            'attachments_mode': attachments.get('attachmentsControlMode', 'N/A'),
            'auto_subscribe': auto_sub.get('autoSubscribe', 'N/A'),
            'auto_subscribe_default': auto_sub.get('defaultSubscriptionType', 'N/A'),
            'personalization_mode': personalization.get('personalizationControlMode', 'N/A'),
            'qapps_mode': qapps_config.get('qAppsControlMode', 'N/A'),
            'quicksight_namespace': quicksight_config.get('clientNamespace', 'N/A'),
            
            # Chat Controls Configuration
            'blocked_phrases_count': len(blocked_phrases_config.get('blockedPhrases', [])),
            'blocked_phrases': '; '.join(blocked_phrases_config.get('blockedPhrases', [])),
            'blocked_phrases_system_message': blocked_phrases_config.get('systemMessageOverride', 'N/A'),
            'creator_mode_control': creator_mode.get('creatorModeControl', 'N/A'),
            'hallucination_reduction_control': hallucination_reduction.get('hallucinationReductionControl', 'N/A'),
            'orchestration_control': orchestration.get('control', 'N/A'),
            'response_scope': chat_controls.get('responseScope', 'N/A') if chat_controls else 'N/A',
            
            # Topic Configurations
            'topic_count': len(topic_configs),
            'topic_names': ', '.join([t.get('name', 'N/A') for t in topic_configs]),
            'topic_descriptions': ' | '.join([f"{t.get('name', 'N/A')}: {t.get('description', 'N/A')}" for t in topic_configs]),
            
            # Error Details
            'error_code': app.get('error', {}).get('errorCode', 'N/A'),
            'error_message': app.get('error', {}).get('errorMessage', 'N/A'),
            
            # Index Info
            'index_id': index_id or 'N/A',
            
            # Data Sources Summary
            'data_source_count': len(data_sources),
            'data_source_ids': ', '.join([ds.get('dataSourceId', 'N/A') for ds in data_sources]),
            'data_source_types': ', '.join([ds.get('type', 'N/A') for ds in data_sources]),
            'data_source_names': ', '.join([ds.get('displayName', 'N/A') for ds in data_sources]),
            'data_source_statuses': ', '.join([ds.get('status', 'N/A') for ds in data_sources]),
            
            # Retriever Summary
            'retriever_count': len(retrievers),
            'retriever_ids': ', '.join([r.get('retrieverId', 'N/A') for r in retrievers]),
            'retriever_types': ', '.join([r.get('type', 'N/A') for r in retrievers]),
            'retriever_statuses': ', '.join([r.get('status', 'N/A') for r in retrievers]),
            
            # Plugin Summary
            'plugin_count': len(plugins),
            'plugin_ids': ', '.join([p.get('pluginId', 'N/A') for p in plugins]),
            'plugin_types': ', '.join([p.get('type', 'N/A') for p in plugins]),
            'plugin_statuses': ', '.join([p.get('status', 'N/A') for p in plugins]),
            
            # Metadata
            'export_timestamp': datetime.now().isoformat(),
            'aws_region': self.aws_region,
        }
        
        return row
    
    def export_to_csv(self, data, filename=None):
        """Export configuration data to CSV"""
        if not data:
            print("⚠️  No data to export")
            return
        
        # Ensure output directory
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qbusiness_config_{timestamp}.csv"
        
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
        """Export configuration data to JSON"""
        if not data:
            return
        
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qbusiness_config_{timestamp}.json"
        
        output_path = output_dir / filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ JSON exported to: {output_path}")
            
        except Exception as e:
            print(f"❌ Error exporting JSON: {e}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Export Q Business application configurations'
    )
    parser.add_argument(
        '--config',
        default='./input/config.yml',
        help='Path to configuration YAML file'
    )
    parser.add_argument(
        '--env',
        default='./config/.env',
        help='Path to .env file with AWS credentials'
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 100)
    print("Q BUSINESS CONFIGURATION EXPORT TOOL")
    print("=" * 100)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Config: {args.config}")
    print(f"Credentials: {args.env}")
    print("=" * 100)
    print()
    
    # Initialize exporter
    print("🔧 Initializing...")
    exporter = QBusinessConfigExporter(args.config, args.env)
    
    # Verify credentials
    if not exporter.verify_credentials():
        print("❌ Exiting due to credential issues")
        return
    
    print("🚀 Starting configuration export...\n")
    
    # Export all configurations
    configs = exporter.export_all_configurations()
    
    if configs:
        print("=" * 100)
        print("📊 EXPORTING DATA")
        print("=" * 100)
        print()
        
        # Export to CSV
        exporter.export_to_csv(configs)
        
        # Export to JSON
        exporter.export_to_json(configs)
        
        print("\n" + "=" * 100)
        print("📈 SUMMARY")
        print("=" * 100)
        print(f"   Applications Processed: {len(configs)}")
        print(f"   Output Directory: ./output/")
        print("=" * 100)
        print("\n✅ Done!")
    else:
        print("⚠️  No configurations found to export")


if __name__ == "__main__":
    main()
