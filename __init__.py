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

# Plugin details
plugin_name = 'sigscan'

# Repository details
repo_owner = 'rikodot'
repo_name = 'binja_native_sigscan'
file_url = 'https://github.com/{}/{}/releases/latest/download'.format(repo_owner, repo_name)

# File names in release section on github along with Binary Ninja versions for which they were compiled (leave whole variable blank if platform not supported)
# Both version variables are inclusive meaning any Binary Ninja version in between is supported, DO NOT include '-dev' suffix so instead of '3.4.4189-dev', use just '3.4.4189')
# You can also support all dev version by replacing both versions with 'DEV' (example below), this is useful because new dev versions roll out almost on daily basis
# but the problem is when dev version becomes stable, the loader must be updated accordingly
# Example:
# win_files = [
#    ('3.1.3469', '3.3.3996', 'sigscan.dll'), # anything in between 3.1.3469 and 3.3.3996 (inclusive) - specific stable versions
#    ('3.4.4169', '3.4.4189', 'sigscan_dev.dll'), # anything in between 3.4.4169 and 3.4.4189 (inclusive) - specific dev versions
#    ('DEV', 'DEV', 'sigscan_dev2.dll'), # anything in between 3.4.4169 and 3.4.4189 (inclusive) - all dev versions
#    ]
win_files = [
    ('3.3.3996', '3.3.3996', '3996sigscan.dll'),
    ('3.4.4271', '3.4.4271', '4271sigscan.dll'),
    ('3.5.4526', '3.5.4526', '4526sigscan.dll'),
    ('DEV', 'DEV', 'DEVsigscan.dll')
    ]
linux_files = [
    ('3.3.3996', '3.3.3996', '3996libsigscan.so'),
    ('3.4.4271', '3.4.4271', '4271libsigscan.so'),
    ('3.5.4526', '3.5.4526', '4526libsigscan.so'),
    ('4.0.4911', '4.0.4911', '4911libsigscan.so'),
    ('4.0.4958', '4.0.4958', '4958libsigscan.so'),
    ('DEV', 'DEV', 'DEVlibsigscan.so')
    ]
darwin_files = [
    ('3.3.3996', '3.3.3996', '3996libsigscan.dylib'),
    ('3.4.4271', '3.4.4271', '4271libsigscan.dylib'),
    ('3.5.4526', '3.5.4526', '4526libsigscan.dylib'),
    ('4.0.4911', '4.0.4911', '4911libsigscan.dylib'),
    ('4.0.4958', '4.0.4958', '4958libsigscan.dylib'),
    ('DEV', 'DEV', 'DEVlibsigscan.dylib')
    ]

# Function that determines whether Binary Ninja version is supported (returns None if not, according file name if yes)
def is_version_supported(files):
    # Get current Binary Ninja version
    version_numbers = binaryninja.core_version().split()[0].split('-')[0].split('.')
    major, minor, build = map(int, version_numbers)
    dev_file = None

    # Loop through files for current platform and see if our version is supported by any
    for entry in files:
        min_ver, max_ver, file = entry

        # first check all non dev versions (there might be specific binary for specific dev versions so use that and if none found then we can use binary for all dev versions)
        if (min_ver != 'DEV' and max_ver != 'DEV'):
            min_parts = min_ver.split('.')
            max_parts = max_ver.split('.')

            major_match = (major >= int(min_parts[0]) and major <= int(max_parts[0]))
            minor_match = (minor >= int(min_parts[1]) and minor <= int(max_parts[1]))
            build_match = (build >= int(min_parts[2]) and build <= int(max_parts[2]))

            if major_match and minor_match and build_match:
                return file
        else:
            dev_file = file
    
    # If we are on dev, check if there is a file for all dev versions
    if ('-dev' in binaryninja.core_version() and dev_file != None and len(dev_file) > 0):
        return dev_file

    return None

# Function that determines whether system is supported
def is_system_supported(file_name):
    return file_name != None and len(file_name) > 0

# Function that determines whether native_plugins_data folder exists
def data_folder_exists():
    return os.path.isdir(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data'))

# Function that determines whether current_native_plugin_data file exists
def data_file_exists():
    return os.path.isfile(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'))

# Function that determines whether temp folder exists
def temp_folder_exists():
    return os.path.isdir(os.path.join(binaryninja.user_plugin_path(), 'temp'))

# Function that reads current_native_plugin_data file
def read_data_file():
    with open(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'), 'r') as f:
        return f.read().splitlines()
    
# Function that writes to current_native_plugin_data file
def write_data_file(version, hash, file_name):
    with open(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'), 'w') as f:
        f.write(version + '\n' + hash + '\n' + file_name)

# Function that deletes file from current_native_plugin_data
def delete_data_file():
    path = os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data')
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception as error:
            return path
    return True

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
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except Exception as error:
            return file_path
    return True

# Function that deletes file from temp directory
def delete_file_from_temp(file_name):
    path = os.path.join(binaryninja.user_plugin_path(), 'temp', file_name)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception as error:
            return path
    return True

# Function that determines whether plugin is installed (for current Binary Ninja version)
def is_plugin_installed(file_name):
    return os.path.isfile(os.path.join(binaryninja.user_plugin_path(), file_name))

# Function that alerts user
def alert_user(description):
    binaryninja.interaction.show_message_box('{} (Native plugin loader)'.format(plugin_name), description, binaryninja.enums.MessageBoxButtonSet.OKButtonSet, binaryninja.enums.MessageBoxIcon.InformationIcon)

# Function that does the actual work
def check_for_updates(repo_owner, repo_name, file_url, win_files, linux_files, darwin_files):
    # Determine OS we are running on
    platform = sys.platform.lower()

    # Windows
    if platform.startswith('win'):
        files = win_files
    # Linux
    elif platform.startswith('linux'):
        files = linux_files
    # Mac
    elif platform.startswith('darwin'):
        files = darwin_files
    else:
        alert_user(plugin_name, 'Unsupported platform')
        return
    
    # Check Binary Ninja version and possible get file name for current version
    file = is_version_supported(files)
    if not file:
        version_numbers = binaryninja.core_version().split()[0].split('-')[0].split('.')
        major, minor, build = map(int, version_numbers)
        alert_user('Current version of Binary Ninja ({}) is not supported.'.format(str(major) + '.' + str(minor) + '.' + str(build)))
        return

    # Create url for file we need
    file_url = '{}/{}'.format(file_url, file)

    # Retrieve the HTML of the release page
    release_url = 'https://github.com/{}/{}/releases/latest'.format(repo_owner, repo_name)
    response = requests.get(release_url)
    html = response.content

    # Parse the HTML to extract the release version
    soup = bs4.BeautifulSoup(html, 'html.parser')
    latest_version_tag = getattr(soup.find('span', {'class': 'css-truncate-target'}), 'text', None)
    latest_version = latest_version_tag.strip() if latest_version_tag else None

    # Make sure we have data folder
    if not data_folder_exists():
        os.mkdir(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data'))

    # Make sure we have temp folder
    if not temp_folder_exists():
        os.mkdir(os.path.join(binaryninja.user_plugin_path(), 'temp'))
    else:
        # Delete all files in temp folder
        for file in os.listdir(os.path.join(binaryninja.user_plugin_path(), 'temp')):
            ret = delete_file_from_temp(file)
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return

    # Verify we have correct file
    if (is_system_supported(file) and latest_version != None):
        plugin_data = (read_data_file() if data_file_exists() else None) if data_folder_exists() else None
        # Check if we have all required data (version, hash, file name)
        if plugin_data == None or len(plugin_data) != 3 or plugin_data[0] == None or plugin_data[1] == None or plugin_data[2] == None:
            ret = delete_data_file() if data_file_exists() else True
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return
            plugin_data = None

        data_version = plugin_data[0] if plugin_data != None else None
        data_hash = plugin_data[1] if plugin_data != None else None
        data_file_name = plugin_data[2] if plugin_data != None else None

        # Check if we there is a binary for different Binary Ninja version
        if (data_file_name != None and data_file_name != file):
            # Delete old file
            ret = delete_file(os.path.join(binaryninja.user_plugin_path(), data_file_name))
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return
            # Delete data file
            ret = delete_data_file()
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return
            # Reset data
            plugin_data = None
            data_version = None
            data_hash = None
            data_file_name = None

        if not is_plugin_installed(file):
            # Plugin not installed, just download it
            if download_file(file_url, file):
                # Register plugin in data directory
                write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                alert_user('Plugin downloaded successfully, please restart Binary Ninja to load it')
            else:
                alert_user('Failed to download plugin')
        else:
            # Plugin installed, no data about the plugin
            if (data_version == None and data_hash == None):
                # Download latest version of the plugin and check if we have that version
                download_file_to_temp(file_url, file)
                if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                    # We have the latest version, register it in data directory
                    write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                    ret = delete_file_from_temp(file)
                    if ret != True:
                        alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                        return
                else:
                    # We don't have the latest version, alert user
                    alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
            # Plugin installed, but data shows it's outdated
            elif (data_version != latest_version):
                # Make sure the version in the data directory is actually the version we have installed (we compare hashes - hash now and hash when we downloaded the plugin)
                if (data_hash == calculate_hash(os.path.join(binaryninja.user_plugin_path(), file))):
                    # Yep, version noted in data corresponds to the hash of currently installed plugin
                    alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
                else:
                    # Nope, version noted in data doesn't correspond to the hash of currently installed plugin (user probably replaced the plugin)
                    ret = delete_data_file()
                    if ret != True:
                        alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                        return
                    # Download latest version of the plugin and check if we have that version
                    download_file_to_temp(file_url, file)
                    if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                        # We have the latest version, register it in data directory so user is not prompted to update as he probably already did
                        write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                        delete_file_from_temp(file)
                    else:
                        # We don't have the latest version, alert user
                        alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
            # Plugin installed, data shows it's up to date, but let's make sure
            elif (data_version == latest_version):
                # Make sure the version in the data directory is actually the version we have installed (we compare hashes - hash now and hash when we downloaded the plugin)
                if (data_hash != calculate_hash(os.path.join(binaryninja.user_plugin_path(), file))):
                    # Nope, hash noted in data doesn't correspond to the hash of currently installed plugin (user probably replaced the plugin with different version)
                    ret = delete_data_file()
                    if ret != True:
                        alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                        return
                    # Let's check if our plugin matches the hash in the latest github release (developer could have replaced file in the github release and user updated to it)
                    download_file_to_temp(file_url, file)
                    if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                        # Yep, hash of the plugin in the github release corresponds to the hash of currently installed plugin so we have the latest one
                        write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                        ret = delete_file_from_temp(file)
                        if ret != True:
                            alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                            return
                    else:
                        # Not the latest one (according to the hash in the github release), but user might be intending to test different version of the plugin, add ignore option
                        alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
    else:
        alert_user('This plugin is not supported on current platform or plugin not found or its github releases not found')

class Updater(binaryninja.BackgroundTaskThread):
    def __init__(self):
        binaryninja.BackgroundTaskThread.__init__(self, 'Native plugin loader - checking for updates on: {}'.format(plugin_name), True)

    def run(self):
        check_for_updates(repo_owner, repo_name, file_url, win_files, linux_files, darwin_files)

obj = Updater()
obj.start()