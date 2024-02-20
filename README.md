**For full readme and source code of native sigscan plugin check out [binja_native_sigscan](https://github.com/rikodot/binja_native_sigscan).**<br>
This python script serves just as a loader for the actual plugin since it is written in C++ and might not be directly used with Binary Ninja's plugin manager.<br>

![preview](https://github.com/rikodot/binja_native_sigscan/blob/main/preview.gif)

### How it works
On the start of Binary Ninja, this script checks if the related native plugin is present and either downloads it or verifies its version using native plugin's github repository. Native plugin requires its own repository which is also used for updating. Each native plugin requires its own loader. Unless there is a bug within this python script or an update is required or highly beneficial, this script is not supposed to be updated as it servers just as a loader. Exact behaviour is described within the script itself.

### If you want to do the same
1. create your native plugin for Binary Ninja
2. configure the script, there are 7 variables to be filled on the beginning of the file
3. follow official Binary Ninja's tutorial on how to write plugins
4. create one github repository for the native plugin itself (use github releases to push updates, each release needs to contain binaries for all supported operating systems - if you want to support let's say only linux, leave windows and macos variables in the script blank - read comments within the script or check out the example above for more context)
5. create second github repository for the loader (this is the one you are going to submit to the Binary Ninja's [community repository](https://github.com/Vector35/community-plugins))
6. for updating the native plugin, push a new release on **its** github repository, this loader will prompt all users to update on the next start of Binary Ninja

### Binary Ninja version problems
Compiled native plugins are usable only on specific versions of Binary Ninja based on API version used. Changing versions in Binary Ninja is fairly easy and switching in between them to test your native plugin should not take much time.<br>
- 3.3.3996
  - `core_version()` returns `'3.3.3996 Personal'`
  - `core_version_info()` returns `CoreVersionInfo(major=3, minor=3, build=3996, channel='Local')`
- 3.2.3814
  - `core_version()` returns `'3.2.3814 Personal'`
  - `core_version_info()` returns `CoreVersionInfo(major=3, minor=2, build=0, channel='Local')` - perhaps the build variable being 0 is a bug?
- 3.1.3469
  - `core_version()` returns `'3.1.3469 Personal'`
  - `core_version_info()` returns `not yet implemented`

For this reason I decided to use `core_version()` to determine current version of Binary Ninja.<br>
As an example let's say you used 3.1.3469's API version to compile your native plugin. You should test each and every Binary Ninja version until you find the lowest and highest supported version. When you are done testing, make sure to setup variables accordingly. More detailed information regarding this can be found along with examples in the script comments.<br>
You can compile your native plugin for multiple Binary Ninja versions to have the widest compatibility (switch version in Binary Ninja -> follow [build process](https://github.com/rikodot/binja_native_sigscan#build-process) - in order to compile native plugin you need to have according Binary Ninja version currently installed or save and re-link static libraries for each Binary Ninja version from `C:\Program Files\Vector35\BinaryNinja`). When switching from one Binary Ninja version to a different one, old native plugin will be loaded and unloaded right after due to API version mismatch producing an error in the log. There is nothing loader can do to prevent this from happening, however this should occur only on the first start of Binary Ninja after switching versions as loader will delete incompatible binary and download compatible one, if found.

### Known issues
- in order to update or delete native plugins, Binary Ninja must be closed (at least on Windows), therefore updating must be done manually (for now)
