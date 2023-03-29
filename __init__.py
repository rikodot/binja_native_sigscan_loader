import os
import sys
import requests
import bs4
import binaryninja

# Logic:
# ver, hash = native_plugins_data folder exists ? (current_native_plugin_data file exists ? ver, hash : none) : none
# plugin_found = current_native_plugin file exists ? true : false
# if !plugin_found -> download plugin && create (or overwrite) current_native_plugin_data file containing latest ver and latest hash
# if plugin_found && ver != latest_ver && ver != none && hash == downloaded plugin hash -> alert user he is using outdated plugin (with link to latest release)
# if plugin_found && ver != latest_ver && ver != none && hash != downloaded plugin hash -> delete current_native_plugin_data file &&
#                                                                    download latest plugin to temp, calculate its hash &&
#                                                                    if latest_hash == downloaded plugin hash -> save latest_hash and latest_ver to current_native_plugin_data file &&
#                                                                           delete file in temp
# if plugin_found && ver == latest_ver && hash != downloaded plugin hash -> delete current_native_plugin_data file && download latest plugin to temp, calculate its hash &&
#                                                                    if latest_hash == downloaded plugin hash -> save latest_hash and latest_ver to current_native_plugin_data file &&
#                                                                           delete file in temp
#                                                                    if latest_hash != downloaded plugin hash -> alert to update (with link to latest release)
# if plugin_found && ver == none && hash == none -> download latest plugin to temp, calculate its hash &&
#                                                                    if latest_hash == downloaded plugin hash -> save latest_hash and latest_ver to current_native_plugin_data file &&
#                                                                           delete file in temp
#                                                                    if latest_hash != downloaded plugin hash -> alert to update (with link to latest release)

# Function that determines whether system is supported
def is_system_supported(file_name):
    return file_name != None and len(file_name) > 0

# Function that determines whether native_plugins_data folder exists
def data_folder_exists():
    return os.path.isdir(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data'))

# Function that determines whether current_native_plugin_data file exists
def data_file_exists(plugin_name):
    return os.path.isfile(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'))

# Function that determines whether temp folder exists
def temp_folder_exists():
    return os.path.isdir(os.path.join(binaryninja.user_plugin_path(), 'temp'))

# Function that reads current_native_plugin_data file
def read_data_file(plugin_name):
    with open(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'), 'r') as f:
        return f.read().splitlines()
    
# Function that writes to current_native_plugin_data file
def write_data_file(plugin_name, version, hash):
    with open(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'), 'w') as f:
        f.write(version + '\n' + hash)

# Function that deletes file from current_native_plugin_data
def delete_data_file(plugin_name):
    os.remove(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'))

# Function that calculates hash of file
def calculate_hash(file_path):
    import hashlib
    hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash.hexdigest()

# Function that downloads file
def download_file(file_url, file_name):
    response = requests.get(file_url)
    if response.status_code == 200:
        with open(os.path.join(binaryninja.user_plugin_path(), file_name), 'wb') as f:
            f.write(response.content)
        return True
    else:
        return False
    
# Function that downloads file to temp directory
def download_file_to_temp(file_url, file_name):
    response = requests.get(file_url)
    if response.status_code == 200:
        with open(os.path.join(binaryninja.user_plugin_path(), 'temp', file_name), 'wb') as f:
            f.write(response.content)
        return True
    else:
        return False

# Function that deletes file
def delete_file(file_path):
    os.remove(file_path)

# Function that deletes file from temp directory
def delete_file_from_temp(file_name):
    os.remove(os.path.join(binaryninja.user_plugin_path(), 'temp', file_name))

# Function that determines whether plugin is installed
def is_plugin_installed(file_name):
    return os.path.isfile(os.path.join(binaryninja.user_plugin_path(), file_name))

# Function that determines whether plugin is outdated
def is_plugin_outdated(plugin_name, version, hash):
    if data_folder_exists():
        if data_file_exists(plugin_name):
            data = read_data_file(plugin_name)
            if data[0] == version and data[1] == hash:
                return False
            else:
                return True
        else:
            return True
    else:
        return True

# Function that alerts user
def alert_user(plugin_name, description):
    binaryninja.interaction.show_message_box('{} (Native plugin loader)'.format(plugin_name), description, binaryninja.enums.MessageBoxButtonSet.OKButtonSet, binaryninja.enums.MessageBoxIcon.InformationIcon)

# Plugin details
plugin_name = 'sigscan'

# Repository details
repo_owner = 'rikodot'
repo_name = 'binja_native_sigscan'
file_url = 'https://github.com/{}/{}/releases/latest/download'.format(repo_owner, repo_name)

# Name of files in release section on github (leave blank if platform not supported)
win_file = 'sigscan.dll'
linux_file = ''
darwin_file = ''

# Retrieve the HTML of the release page
release_url = 'https://github.com/{}/{}/releases/latest'.format(repo_owner, repo_name)
response = requests.get(release_url)
html = response.content

# Parse the HTML to extract the release version
soup = bs4.BeautifulSoup(html, 'html.parser')
latest_version_tag = getattr(soup.find('span', {'class': 'css-truncate-target'}), 'text', None)
latest_version = latest_version_tag.strip() if latest_version_tag else None

# Determine OS we are running on
platform = sys.platform.lower()

# Windows
if platform.startswith('win'):
    file_url = '{}/{}'.format(file_url, win_file)
    file = win_file
# Linux
elif platform.startswith('linux'):
    file_url = '{}/{}'.format(file_url, linux_file)
    file = linux_file
# Mac
elif platform.startswith('darwin'):
    file_url = '{}/{}'.format(file_url, darwin_file)
    file = darwin_file
else:
    alert_user(plugin_name, 'Unsupported platform')

# Make sure we have data folder
if not data_folder_exists():
    os.mkdir(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data'))

# Make sure we have temp folder
if not temp_folder_exists():
    os.mkdir(os.path.join(binaryninja.user_plugin_path(), 'temp'))
else:
    # Delete all files in temp folder
    for file in os.listdir(os.path.join(binaryninja.user_plugin_path(), 'temp')):
        delete_file_from_temp(file)

# Do the thing
if (is_system_supported(file) and latest_version != None):
    plugin_data = (read_data_file(plugin_name) if data_file_exists(plugin_name) else None) if data_folder_exists() else None
    # Check if we have both version and hash of the plugin
    if plugin_data == None or len(plugin_data) != 2 or plugin_data[0] == None or plugin_data[1] == None:
        delete_data_file(plugin_name) if data_file_exists(plugin_name) else None
        plugin_data = None
    
    data_version = plugin_data[0] if plugin_data != None else None
    data_hash = plugin_data[1] if plugin_data != None else None
    if not is_plugin_installed(file):
        # Plugin not installed, just download it
        if download_file(file_url, file):
            # Register plugin in data directory
            write_data_file(plugin_name, latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)))
            alert_user(plugin_name, 'Plugin downloaded successfully, please restart Binary Ninja to load it')
        else:
            alert_user(plugin_name, 'Failed to download plugin')
    else:
        # Plugin installed, no data about the plugin
        if (data_version == None and data_hash == None):
            # Download latest version of the plugin and check if we have that version
            download_file_to_temp(file_url, file)
            if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                # We have the latest version, register it in data directory
                write_data_file(plugin_name, latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)))
                delete_file_from_temp(file)
            else:
                # We don't have the latest version, alert user
                alert_user(plugin_name, 'You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
        # Plugin installed, but data shows it's outdated
        elif (data_version != latest_version):
            # Make sure the version in the data directory is actually the version we have installed (we compare hashes - hash now and hash when we downloaded the plugin)
            if (data_hash == calculate_hash(os.path.join(binaryninja.user_plugin_path(), file))):
                # Yep, version noted in data corresponds to the hash of currently installed plugin
                alert_user(plugin_name, 'You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
            else:
                # Nope, version noted in data doesn't correspond to the hash of currently installed plugin (user probably replaced the plugin)
                delete_data_file(plugin_name)
                # Download latest version of the plugin and check if we have that version
                download_file_to_temp(file_url, file)
                if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                    # We have the latest version, register it in data directory so user is not prompted to update as he probably already did
                    write_data_file(plugin_name, latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)))
                    delete_file_from_temp(file)
                else:
                    # We don't have the latest version, alert user
                    alert_user(plugin_name, 'You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
        # Plugin installed, data shows it's up to date, but let's make sure
        elif (data_version == latest_version):
            # Make sure the version in the data directory is actually the version we have installed (we compare hashes - hash now and hash when we downloaded the plugin)
            if (data_hash != calculate_hash(os.path.join(binaryninja.user_plugin_path(), file))):
                # Nope, hash noted in data doesn't correspond to the hash of currently installed plugin (user probably replaced the plugin with different version)
                delete_data_file(plugin_name)                
                # Let's check if our plugin matches the hash in the latest github release (developer could have replaced file in the github release and user updated to it)
                download_file_to_temp(file_url, file)
                if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                    # Yep, hash of the plugin in the github release corresponds to the hash of currently installed plugin so we have the latest one
                    write_data_file(plugin_name, latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)))
                    delete_file_from_temp(file)
                else:
                    # Not the latest one (according to the hash in the github release), but user might be intending to test different version of the plugin, add ignore option
                    alert_user(plugin_name, 'You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
else:
    alert_user(plugin_name, 'This plugin is not supported on current platform or plugin not found or its github releases not found')