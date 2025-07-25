#!/bin/bash

# Refold Helper Bot - Project Knowledge Sync Script v1.0
# This script copies all relevant files to ai_context/ folder for Claude context

set -e  # Exit on error

# Configuration
readonly CONTEXT_DIR="ai_context"
readonly BACKUP_DIR="${CONTEXT_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
readonly PROJECT_NAME="Refold Helper Bot"

# Colors
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
success() { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; }

generate_project_structure() {
    info "🌳 Generating project structure..."
    
    if command -v tree >/dev/null 2>&1; then
        # Use tree if available, exclude common irrelevant directories
        tree -I '__pycache__|*.pyc|.git|*.log|dist|build|ai_context|*.dat' -a -L 5 > "${CONTEXT_DIR}/project_structure.txt"
    else
        # Fallback using find
        {
            echo "PROJECT STRUCTURE (generated with find):"
            echo "========================================"
            find . -type f \( \
                -name "*.py" -o \
                -name "*.md" -o \
                -name "*.txt" -o \
                -name "*.json" -o \
                -name "*.tsv" -o \
                -name "*.yml" -o \
                -name "*.yaml" -o \
                -name "*.toml" -o \
                -name "*.cfg" -o \
                -name "*.ini" \
            \) \
            -not -path "./.git/*" \
            -not -path "./__pycache__/*" \
            -not -path "./ai_context/*" \
            | sort
        } > "${CONTEXT_DIR}/project_structure.txt"
    fi
    
    success "Project structure generated"
}

copy_source_files() {
    info "🐍 Copying Python source files..."
    local source_count=0
    
    # Find all Python files
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then
            # Create flattened name: config/settings.py -> config__settings.py
            local flat_name
            flat_name=$(echo "$file" | sed 's|^\./||' | sed 's|/|__|g')
            
            cp "$file" "${CONTEXT_DIR}/$flat_name"
            echo "  ✓ $file -> $flat_name"
            source_count=$((source_count + 1))
        fi
    done < <(find . -name "*.py" -not -path "./__pycache__/*" -not -path "./ai_context/*" -print0)
    
    success "Python files: $source_count copied"
}

copy_data_files() {
    info "📊 Copying data files..."
    local data_count=0
    
    # Copy TSV and JSON files (skip binary .dat files)
    for ext in tsv json csv; do
        while IFS= read -r -d '' file; do
            if [ -f "$file" ]; then
                local flat_name
                flat_name=$(echo "$file" | sed 's|^\./||' | sed 's|/|__|g')
                
                cp "$file" "${CONTEXT_DIR}/$flat_name"
                echo "  ✓ $file -> $flat_name"
                data_count=$((data_count + 1))
            fi
        done < <(find . -name "*.$ext" -not -path "./ai_context/*" -print0)
    done
    
    success "Data files: $data_count copied"
}

copy_config_files() {
    info "⚙️  Copying configuration files..."
    local config_count=0
    
    # Common Python config files
    local config_files=(
        "requirements.txt"
        "requirements-dev.txt" 
        "setup.py"
        "setup.cfg"
        "pyproject.toml"
        "poetry.lock"
        "Pipfile"
        "Pipfile.lock"
        ".env.example"
        ".env.template"
        "runtime.txt"
        "Dockerfile"
        "docker-compose.yml"
        "docker-compose.yaml"
        ".gitignore"
        ".dockerignore"
    )
    
    for file in "${config_files[@]}"; do
        if [ -f "$file" ]; then
            cp "$file" "${CONTEXT_DIR}/"
            echo "  ✓ $file"
            config_count=$((config_count + 1))
        fi
    done
    
    success "Configuration files: $config_count copied"
}

copy_documentation() {
    info "📚 Copying documentation files..."
    local doc_count=0
    
    # Copy markdown and text files
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then
            local flat_name
            flat_name=$(echo "$file" | sed 's|^\./||' | sed 's|/|__|g')
            
            cp "$file" "${CONTEXT_DIR}/$flat_name"
            echo "  ✓ $file -> $flat_name"
            doc_count=$((doc_count + 1))
        fi
    done < <(find . \( -name "*.md" -o -name "*.txt" -o -name "*.rst" \) -not -path "./ai_context/*" -print0)
    
    success "Documentation files: $doc_count copied"
}

create_project_overview() {
    info "📋 Creating project overview..."
    
    local total_files
    total_files=$(find "${CONTEXT_DIR}" -type f | wc -l)
    
    {
        echo "# ${PROJECT_NAME} - AI Context Package"
        echo "Generated: $(date)"
        echo "Total files: $total_files"
        echo ""
        echo "## Project Overview"
        echo "This is a comprehensive Discord bot for the Refold language learning community."
        echo "The bot manages cross-server role synchronization, automated community features,"
        echo "and provides quick access to learning resources across 13+ language servers."
        echo ""
        echo "## Architecture"
        echo "- **Main Entry:** SpanishBot.py (despite the name, it's a multi-language bot)"  
        echo "- **Configuration:** config/ package with settings and constants"
        echo "- **Features:** cogs/ package with feature-based modules"
        echo "- **Data:** Various TSV/JSON files for persistence and configuration"
        echo ""
        echo "## File Categories"
        echo ""
        echo "### Python Source Files"
        find "${CONTEXT_DIR}" -name "*.py" | sort | sed 's/^/- /'
        echo ""
        echo "### Configuration Files"  
        find "${CONTEXT_DIR}" \( -name "*.txt" -o -name "*.json" -o -name "*.yml" -o -name "*.yaml" -o -name "*.toml" \) | grep -v "\.py" | sort | sed 's/^/- /'
        echo ""
        echo "### Data Files"
        find "${CONTEXT_DIR}" \( -name "*.tsv" -o -name "*.csv" \) | sort | sed 's/^/- /'
        echo ""
        echo "### Documentation"
        find "${CONTEXT_DIR}" -name "*.md" | sort | sed 's/^/- /'
        echo ""
        echo "## Key Features"
        echo "- Cross-server role synchronization across language communities"
        echo "- Automated daily/weekly accountability threads"
        echo "- Reaction-based role assignment system"  
        echo "- Community project management with private channels"
        echo "- Resource lookup system (videos, documentation)"
        echo "- Moderation tools and FAQ automation"
        echo "- Analytics and member tracking across servers"
        echo ""
        echo "## Development Status"
        echo "✅ **Phase 1 Complete:** Configuration management with environment variables"
        echo "✅ **Phase 2 Complete:** Cogs architecture with feature-based modules"
        echo "🔄 **Phase 3 Pending:** Service layer for business logic separation"
        echo "🔄 **Phase 4 Pending:** Unified data storage system"
        echo "🔄 **Phase 5 Pending:** Comprehensive logging and error handling"
        echo ""
        echo "## Usage"
        echo "\`\`\`bash"
        echo "# Traditional method"
        echo "python3 SpanishBot.py YOUR_BOT_TOKEN"
        echo ""
        echo "# Environment variable method"
        echo "export BOT_TOKEN=\"your_token\""
        echo "python3 SpanishBot.py"
        echo "\`\`\`"
    } > "${CONTEXT_DIR}/PROJECT_OVERVIEW.md"
    
    success "Project overview created"
}

create_file_inventory() {
    info "📦 Creating detailed file inventory..."
    
    local total_files
    total_files=$(find "${CONTEXT_DIR}" -type f | wc -l)
    
    {
        echo "=== ${PROJECT_NAME} - COMPLETE FILE INVENTORY ==="
        echo "Generated: $(date)"
        echo "Total files: $total_files"
        echo "Context directory: ${CONTEXT_DIR}/"
        echo ""
        echo "=== MAIN BOT FILES ==="
        find "${CONTEXT_DIR}" -name "SpanishBot.py" -o -name "doclist.py" | sort
        echo ""
        echo "=== CONFIGURATION MODULE ==="
        find "${CONTEXT_DIR}" -name "config__*.py" | sort
        echo ""
        echo "=== COGS (FEATURE MODULES) ==="
        find "${CONTEXT_DIR}" -name "cogs__*.py" | sort  
        echo ""
        echo "=== DATA FILES ==="
        find "${CONTEXT_DIR}" \( -name "*.tsv" -o -name "*.csv" -o -name "*.json" \) | sort
        echo ""
        echo "=== CONFIGURATION FILES ==="
        find "${CONTEXT_DIR}" \( -name "requirements*.txt" -o -name "setup.*" -o -name "*.toml" -o -name "Dockerfile*" -o -name ".env*" -o -name ".gitignore" \) | sort
        echo ""
        echo "=== DOCUMENTATION ==="
        find "${CONTEXT_DIR}" \( -name "*.md" -o -name "*.txt" \) -not -name "requirements*.txt" | sort
        echo ""
        echo "=== PROJECT STRUCTURE ==="
        find "${CONTEXT_DIR}" -name "project_structure.txt"
        echo ""
        echo "=== COMPLETE FILE LIST ==="
        find "${CONTEXT_DIR}" -type f | sort
        echo ""
        echo "=== DIRECTORY SIZE ==="
        du -sh "${CONTEXT_DIR}" 2>/dev/null || echo "Size calculation unavailable"
    } > "${CONTEXT_DIR}/FILE_INVENTORY.txt"
    
    success "File inventory created"
}

main() {
    echo ""
    info "🚀 Starting ${PROJECT_NAME} knowledge sync..."
    echo ""
    
    # Create backup if directory exists and has content
    if [ -d "$CONTEXT_DIR" ] && [ "$(ls -A "$CONTEXT_DIR" 2>/dev/null || echo)" ]; then
        info "📦 Creating backup: $BACKUP_DIR"
        cp -r "$CONTEXT_DIR" "$BACKUP_DIR" || warn "Backup failed, continuing..."
    fi
    
    # Clean and recreate context directory
    rm -rf "${CONTEXT_DIR}"
    mkdir -p "$CONTEXT_DIR"
    
    # Generate project structure first
    generate_project_structure
    
    # Copy all relevant files
    copy_source_files
    copy_data_files  
    copy_config_files
    copy_documentation
    
    # Create overview and inventory
    create_project_overview
    create_file_inventory
    
    # Create sync log
    {
        echo "=== ${PROJECT_NAME} Knowledge Sync Log ==="
        echo "Completed: $(date)"
        echo "Total files: $(find "${CONTEXT_DIR}" -type f | wc -l)"
        echo "Directory size: $(du -sh "${CONTEXT_DIR}" 2>/dev/null | cut -f1 || echo 'Unknown')"
        echo "Status: SUCCESS"
        echo ""
        echo "Ready for Claude upload!"
        echo "Select all files in ${CONTEXT_DIR}/ and drag to Claude interface."
    } > "${CONTEXT_DIR}/sync.log"
    
    # Final summary
    echo ""
    success "🎯 SYNC COMPLETE!"
    echo ""
    info "📁 Total files: $(find "${CONTEXT_DIR}" -type f | wc -l)"
    info "📂 Directory: ${CONTEXT_DIR}/"
    info "💾 Size: $(du -sh "${CONTEXT_DIR}" 2>/dev/null | cut -f1 || echo 'Unknown')"
    echo ""
    success "💡 Ready for Claude upload:"
    success "   1. Open ${CONTEXT_DIR}/ folder"
    success "   2. Select all files (Ctrl+A)"  
    success "   3. Drag and drop into Claude interface"
    echo ""
    
    # Cleanup backup if everything succeeded
    if [ -d "$BACKUP_DIR" ]; then
        rm -rf "$BACKUP_DIR"
        info "🧹 Cleaned up backup"
    fi
    
    info "✨ Knowledge sync complete - project ready for AI context!"
}

# Check if script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
