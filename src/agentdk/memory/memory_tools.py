"""Memory Tools - Investigation and debugging tooling for memory system.

This module provides the MemoryTools class that offers CLI-style commands
for investigating, debugging, and managing memory content without requiring
a separate UI.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import argparse
import io
import sys

logger = logging.getLogger(__name__)


class MemoryTools:
    """Memory investigation and debugging tooling.
    
    Provides CLI-style commands for memory investigation:
    - show: Display memory contents
    - search: Search memory for specific content
    - stats: Memory usage statistics
    - export: Export memory data
    - clear: Clear memory selectively
    - preferences: Manage user preferences
    """
    
    def __init__(self, memory_manager: Any) -> None:
        """Initialize Memory Tools.
        
        Args:
            memory_manager: MemoryManager instance to operate on
        """
        self.memory = memory_manager
        
        # Command mapping
        self.commands = {
            'show': self.show,
            'search': self.search,
            'stats': self.stats,
            'export': self.export,
            'clear': self.clear,
            'preferences': self.preferences
        }
        
        logger.debug("MemoryTools initialized")
    
    def execute(self, command: str) -> str:
        """Execute a memory investigation command.
        
        Args:
            command: CLI-style command string
            
        Returns:
            Formatted response string
        """
        try:
            # Parse command
            parts = command.strip().split()
            if not parts:
                return self._help()
            
            cmd_name = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            if cmd_name not in self.commands:
                return f"Unknown command: {cmd_name}. Use 'help' for available commands."
            
            # Execute command
            return self.commands[cmd_name](args)
            
        except Exception as e:
            logger.error(f"Error executing memory command '{command}': {e}")
            return f"Error: {e}"
    
    def show(self, args: List[str]) -> str:
        """Show memory contents.
        
        Usage: show [--type working|episodic|factual|all] [--format table|json|text]
        """
        # Simple argument parsing without argparse to avoid SystemExit
        type_filter = 'all'
        format_type = 'text'
        
        i = 0
        while i < len(args):
            if args[i] == '--type' and i + 1 < len(args):
                type_filter = args[i + 1]
                i += 2
            elif args[i] == '--format' and i + 1 < len(args):
                format_type = args[i + 1]
                i += 2
            else:
                i += 1
        
        results = {}
        
        # Collect data based on type
        if type_filter in ['working', 'all']:
            results['working'] = self._get_working_memory_data()
        
        if type_filter in ['episodic', 'all']:
            results['episodic'] = self._get_episodic_memory_data()
        
        if type_filter in ['factual', 'all']:
            results['factual'] = self._get_factual_memory_data()
        
        # Format output
        return self._format_output(results, format_type)
    
    def search(self, args: List[str]) -> str:
        """Search memory for specific content.
        
        Usage: search --query "keyword" [--type episodic|factual] [--limit 10]
        """
        query = None
        search_type = 'episodic'
        limit = 10
        
        i = 0
        while i < len(args):
            if args[i] == '--query' and i + 1 < len(args):
                query = args[i + 1]
                i += 2
            elif args[i] == '--type' and i + 1 < len(args):
                search_type = args[i + 1]
                i += 2
            elif args[i] == '--limit' and i + 1 < len(args):
                try:
                    limit = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1
        
        if not query:
            return "Usage: search --query 'keyword' [--type episodic|factual] [--limit 10]"
        
        results = {}
        
        if search_type == 'episodic':
            conversations = self.memory.episodic.search_conversations(query, limit=limit)
            results['episodic_search'] = {
                'query': query,
                'results': conversations,
                'count': len(conversations)
            }
        
        elif search_type == 'factual':
            import asyncio
            facts = asyncio.run(self.memory.factual.retrieve(query, limit=limit))
            results['factual_search'] = {
                'query': query,
                'results': facts,
                'count': len(facts) if isinstance(facts, list) else 1
            }
        
        return self._format_output(results, 'text')
    
    def stats(self, args: List[str]) -> str:
        """Get memory statistics.
        
        Usage: stats [--detailed] [--health] [--compression-info]
        """
        detailed = '--detailed' in args
        health = '--health' in args
        compression_info = '--compression-info' in args
        
        stats = self.memory.get_memory_stats()
        
        if detailed or health or compression_info:
            # Enhanced stats
            enhanced_stats = stats.copy()
            
            if health:
                enhanced_stats['health'] = self._get_memory_health()
            
            if compression_info:
                enhanced_stats['compression_details'] = self._get_compression_info()
            
            return self._format_stats(enhanced_stats, detailed=True)
        
        return self._format_stats(stats, detailed=False)
    
    def export(self, args: List[str]) -> str:
        """Export memory data.
        
        Usage: export --format json|csv [--output file.json] [--type working|episodic|factual]
        """
        format_type = None
        output_path = None
        export_type = 'all'
        
        i = 0
        while i < len(args):
            if args[i] == '--format' and i + 1 < len(args):
                format_type = args[i + 1]
                i += 2
            elif args[i] == '--output' and i + 1 < len(args):
                output_path = args[i + 1]
                i += 2
            elif args[i] == '--type' and i + 1 < len(args):
                export_type = args[i + 1]
                i += 2
            else:
                i += 1
        
        if not format_type:
            return "Usage: export --format json|csv [--output file.json] [--type working|episodic|factual]"
        
        # Generate default filename if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"memory_export_{timestamp}.{format_type}"
        
        try:
            if export_type == 'episodic':
                success = self.memory.episodic.export_conversations(output_path, format_type)
            else:
                # Export all memory types
                success = self._export_all_memory(output_path, format_type)
            
            if success:
                return f"✅ Memory exported to {output_path}"
            else:
                return f"❌ Failed to export memory to {output_path}"
                
        except Exception as e:
            return f"❌ Export failed: {e}"
    
    def clear(self, args: List[str]) -> str:
        """Clear memory selectively.
        
        Usage: clear --type working|episodic|factual [--confirm]
        """
        clear_type = None
        confirm = '--confirm' in args
        
        i = 0
        while i < len(args):
            if args[i] == '--type' and i + 1 < len(args):
                clear_type = args[i + 1]
                i += 2
            else:
                i += 1
        
        if not clear_type:
            return "Usage: clear --type working|episodic|factual [--confirm]"
        
        if not confirm:
            return f"⚠️  This will clear all {clear_type} memory. Add --confirm to proceed."
        
        success = self.memory.clear_memory(clear_type)
        
        if success:
            return f"✅ {clear_type.title()} memory cleared successfully"
        else:
            return f"❌ Failed to clear {clear_type} memory"
    
    def preferences(self, args: List[str]) -> str:
        """Manage user preferences.
        
        Usage: preferences [--list] [--set category key value] [--get category key]
        """
        if '--list' in args:
            import asyncio
            prefs = asyncio.run(self.memory.factual.list_preferences())
            return self._format_preferences(prefs)
        
        # Handle --set
        set_index = -1
        try:
            set_index = args.index('--set')
        except ValueError:
            pass
        
        if set_index >= 0 and set_index + 3 < len(args):
            category = args[set_index + 1]
            key = args[set_index + 2]
            value = args[set_index + 3]
            
            try:
                # Try to parse value as JSON for complex types
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    parsed_value = value
                
                self.memory.set_preference(category, key, parsed_value)
                return f"✅ Preference set: {category}.{key} = {parsed_value}"
            except Exception as e:
                return f"❌ Failed to set preference: {e}"
        
        # Handle --get
        get_index = -1
        try:
            get_index = args.index('--get')
        except ValueError:
            pass
        
        if get_index >= 0 and get_index + 2 < len(args):
            category = args[get_index + 1]
            key = args[get_index + 2]
            
            try:
                value = self.memory.get_preference(category, key)
                if value is not None:
                    return f"{category}.{key} = {value}"
                else:
                    return f"❌ Preference not found: {category}.{key}"
            except Exception as e:
                return f"❌ Failed to get preference: {e}"
        
        return "Usage: preferences [--list] [--set category key value] [--get category key]"
    
    def _help(self) -> str:
        """Get help information."""
        return """
Memory Investigation Commands:

show [--type working|episodic|factual|all] [--format table|json|text]
    Display memory contents

search --query "keyword" [--type episodic|factual] [--limit 10]
    Search memory for specific content

stats [--detailed] [--health] [--compression-info]
    Get memory usage statistics

export --format json|csv [--output file.json] [--type working|episodic|factual]
    Export memory data to file

clear --type working|episodic|factual [--confirm]
    Clear memory selectively

preferences [--list] [--set category key value] [--get category key]
    Manage user preferences

Examples:
    show --type working --format table
    search --query "database" --type episodic
    stats --detailed --health
    export --format json --output backup.json
    preferences --set ui response_format table
"""
    
    def _get_working_memory_data(self) -> Dict[str, Any]:
        """Get working memory data."""
        try:
            import asyncio
            return {
                'recent_context': self.memory.working.get_recent_conversation(),
                'stats': asyncio.run(self.memory.working.get_stats())
            }
        except Exception as e:
            logger.error(f"Error getting working memory data: {e}")
            return {'error': str(e)}
    
    def _get_episodic_memory_data(self, limit: int = 10) -> Dict[str, Any]:
        """Get episodic memory data."""
        try:
            conversations = self.memory.episodic.search_conversations("", limit=limit)
            
            return {
                'recent_conversations': conversations,
                'stats': self.memory.episodic.get_stats()
            }
        except Exception as e:
            logger.error(f"Error getting episodic memory data: {e}")
            return {'error': str(e)}
    
    def _get_factual_memory_data(self) -> Dict[str, Any]:
        """Get factual memory data."""
        try:
            import asyncio
            return {
                'preferences': asyncio.run(self.memory.factual.list_preferences()),
                'stats': asyncio.run(self.memory.factual.get_stats())
            }
        except Exception as e:
            logger.error(f"Error getting factual memory data: {e}")
            return {'error': str(e)}
    
    def _format_output(self, data: Dict[str, Any], format_type: str) -> str:
        """Format output based on format type."""
        if format_type == 'json':
            return json.dumps(data, indent=2, default=str)
        
        elif format_type == 'table':
            return self._format_as_table(data)
        
        else:  # text format
            return self._format_as_text(data)
    
    def _format_as_table(self, data: Dict[str, Any]) -> str:
        """Format data as table."""
        output = []
        
        for memory_type, content in data.items():
            output.append(f"\n=== {memory_type.upper()} MEMORY ===")
            
            if memory_type == 'working' and 'recent_context' in content:
                context = content['recent_context']
                if isinstance(context, list):
                    output.append("Recent Interactions:")
                    for i, interaction in enumerate(context[-5:], 1):
                        output.append(f"  {i}. {interaction.get('user_query', '')[:50]}...")
                        output.append(f"     Response: {interaction.get('agent_response', '')[:50]}...")
            
            elif memory_type == 'episodic' and 'recent_conversations' in content:
                conversations = content['recent_conversations']
                output.append("Recent Conversations:")
                for conv in conversations[:5]:
                    timestamp = conv.get('timestamp', '')
                    query = conv.get('user_query', '')[:40]
                    output.append(f"  {timestamp}: {query}...")
            
            elif memory_type == 'factual' and 'preferences' in content:
                prefs = content['preferences']
                output.append("User Preferences:")
                for category, settings in prefs.items():
                    output.append(f"  [{category}]")
                    for key, value in settings.items():
                        output.append(f"    {key}: {value}")
        
        return "\n".join(output)
    
    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """Format data as readable text."""
        output = []
        
        for memory_type, content in data.items():
            output.append(f"\n🧠 {memory_type.upper()} MEMORY")
            output.append("=" * 40)
            
            if 'error' in content:
                output.append(f"❌ Error: {content['error']}")
                continue
            
            # Add stats if available
            if 'stats' in content:
                stats = content['stats']
                output.append("📊 Statistics:")
                for key, value in stats.items():
                    output.append(f"  • {key}: {value}")
                output.append("")
            
            # Add specific content
            if memory_type == 'working' and 'recent_context' in content:
                context = content['recent_context']
                output.append("💭 Recent Context:")
                if isinstance(context, list) and context:
                    for interaction in context[-3:]:
                        output.append(f"  Q: {interaction.get('user_query', '')}")
                        output.append(f"  A: {interaction.get('agent_response', '')[:100]}...")
                        output.append("")
                else:
                    output.append("  No recent interactions")
            
            elif memory_type == 'episodic' and 'recent_conversations' in content:
                conversations = content['recent_conversations']
                output.append("📖 Recent Conversations:")
                for conv in conversations[:3]:
                    timestamp = conv.get('timestamp', '')
                    query = conv.get('user_query', '')
                    output.append(f"  [{timestamp}] {query}")
                    output.append("")
            
            elif memory_type == 'factual' and 'preferences' in content:
                prefs = content['preferences']
                output.append("🎯 User Preferences:")
                for category, settings in prefs.items():
                    output.append(f"  [{category}]")
                    for key, value in settings.items():
                        output.append(f"    {key}: {value}")
                output.append("")
        
        return "\n".join(output)
    
    def _format_stats(self, stats: Dict[str, Any], detailed: bool = False) -> str:
        """Format memory statistics."""
        output = ["📊 MEMORY STATISTICS", "=" * 30]
        
        for memory_type, data in stats.items():
            if memory_type == 'config':
                continue
                
            output.append(f"\n🧠 {memory_type.upper()} MEMORY:")
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'compression_ratio' and isinstance(value, float):
                        percentage = value * 100
                        output.append(f"  • {key}: {percentage:.1f}%")
                    else:
                        output.append(f"  • {key}: {value}")
        
        # Add configuration info
        if 'config' in stats:
            config = stats['config']
            output.append(f"\n⚙️  CONFIGURATION:")
            for key, value in config.items():
                output.append(f"  • {key}: {value}")
        
        return "\n".join(output)
    
    def _format_preferences(self, preferences: Dict[str, Any]) -> str:
        """Format user preferences."""
        if not preferences:
            return "No preferences set"
        
        output = ["🎯 USER PREFERENCES", "=" * 25]
        
        for category, settings in preferences.items():
            output.append(f"\n[{category}]")
            for key, value in settings.items():
                output.append(f"  {key}: {value}")
        
        return "\n".join(output)
    
    def _get_memory_health(self) -> Dict[str, Any]:
        """Get memory health information."""
        health = {
            'status': 'healthy',
            'issues': []
        }
        
        try:
            stats = self.memory.get_memory_stats()
            
            # Check working memory size
            working_stats = stats.get('working', {})
            if working_stats.get('message_count', 0) > 100:
                health['issues'].append("Working memory has many messages - consider clearing")
            
            # Check episodic compression ratio
            episodic_stats = stats.get('episodic', {})
            compression_ratio = episodic_stats.get('compression_ratio', 0)
            if compression_ratio < 0.1 and episodic_stats.get('total_conversations', 0) > 50:
                health['issues'].append("Low compression ratio - conversations may be using too many tokens")
            
            # Check factual memory size
            factual_stats = stats.get('factual', {})
            if factual_stats.get('total_preferences', 0) > 1000:
                health['issues'].append("Many user preferences stored - consider cleanup")
            
            if health['issues']:
                health['status'] = 'warning'
            
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"Health check failed: {e}")
        
        return health
    
    def _get_compression_info(self) -> Dict[str, Any]:
        """Get detailed compression information."""
        try:
            episodic_stats = self.memory.episodic.get_stats()
            return {
                'total_conversations': episodic_stats.get('total_conversations', 0),
                'compressed_conversations': episodic_stats.get('compressed_conversations', 0),
                'compression_ratio': episodic_stats.get('compression_ratio', 0),
                'token_savings': episodic_stats.get('token_savings', 0),
                'compression_threshold': episodic_stats.get('compression_threshold', 0)
            }
        except Exception as e:
            return {'error': f"Failed to get compression info: {e}"}
    
    def _export_all_memory(self, output_path: str, format_type: str) -> bool:
        """Export all memory types to a single file."""
        try:
            all_data = {
                'working': self._get_working_memory_data(),
                'episodic': self._get_episodic_memory_data(limit=10000),
                'factual': self._get_factual_memory_data(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            if format_type == 'json':
                with open(output_path, 'w') as f:
                    json.dump(all_data, f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Failed to export all memory: {e}")
            return False 