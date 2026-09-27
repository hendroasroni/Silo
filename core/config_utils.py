import os
import re

# Project root directory (parent of core/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
EXAMPLES_DIR = os.path.join(CONFIG_DIR, "examples")
CHANNELS_DIR = os.path.join(PROJECT_ROOT, "channels_youtube")
PROJECTS_WEB_DIR = os.path.join(PROJECT_ROOT, "projects_web")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
LEGACY_YOUTUBE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output_youtube")

def clean_slug(name, fallback_id=""):
    """
    Cleans a project or channel name to be safe for directory usage.
    """
    clean = re.sub(r'[^\w\-_\. ]', '_', str(name)).strip().replace(' ', '_')
    if not clean or clean in ["_", "default"]:
        clean = f"project_{fallback_id}" if fallback_id else "default_project"
    return clean

def get_web_project_dir(site_or_name_or_id):
    """
    Returns the isolated workspace directory for a website project and ensures
    subfolders ('silos', 'drafts', 'exports') exist.
    """
    if isinstance(site_or_name_or_id, dict):
        name = site_or_name_or_id.get("name", "")
        sid = site_or_name_or_id.get("id", "")
        slug = clean_slug(name, sid)
    else:
        slug = clean_slug(str(site_or_name_or_id))
        
    path = os.path.join(PROJECTS_WEB_DIR, slug)
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "silos"), exist_ok=True)
    return path


def get_config_path(filename: str) -> str:
    """
    Resolves the absolute path for a configuration file, token, or key file.
    Search priority:
    1. If already absolute, return as-is.
    2. Check inside config/<filename>
    3. Fallback to project root <filename>
    4. If not found in either, return config/<filename> as default creation target.
    """
    if not filename:
        return filename
    if os.path.isabs(filename):
        return filename
        
    # Check if inside config/
    config_path = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(config_path):
        return config_path
        
    # Check if in project root
    root_path = os.path.join(PROJECT_ROOT, filename)
    if os.path.exists(root_path):
        return root_path
        
    # Default target is inside config/
    return config_path

def get_project_root() -> str:
    return PROJECT_ROOT

def get_config_dir() -> str:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return CONFIG_DIR
