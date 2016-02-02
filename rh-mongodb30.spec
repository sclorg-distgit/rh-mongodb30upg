# Define SCL name
%{!?scl_name_prefix: %global scl_name_prefix rh-}
%{!?scl_name_base: %global scl_name_base mongodb}
%{!?version_major: %global version_major 3}
%{!?version_minor: %global version_minor 0}
%{!?scl_name_suffix: %global scl_name_suffix upg}
%{!?scl_name_version: %global scl_name_version %{version_major}%{version_minor}}
%{!?scl: %global scl %{scl_name_prefix}%{scl_name_base}%{scl_name_version}%{?scl_name_suffix}}

# Turn on new layout -- prefix for packages and location
# for config and variable files
# This must be before calling %%scl_package
%{!?nfsmountable: %global nfsmountable 1}

# Define SCL macros
%{?scl_package:%scl_package %scl}

# needed, because we can't use Requires: %%{?scl_v8_%%{scl_name_base}}
%global scl_v8 v8314
%global scl_v8_prefix %{scl_v8}-

# do not produce empty debuginfo package (https://bugzilla.redhat.com/show_bug.cgi?id=1061439#c2)
%global debug_package %{nil}

# Convert SCL name into uppercase including - to _ conversion
%if 0%{?scl:1}
%global scl_upper %{lua:print(string.upper(string.gsub(rpm.expand("%{scl}"), "-", "_")))}
%endif

Summary:	Package that installs %{scl}
Name:		%{scl}
Version:	2.2
Release:	2%{?dist}
License:	GPLv2+
Group:		Applications/File
# template of man page with RPM macros to be expanded
Source0:	README
# mongodb license
Source1:	LICENSE
Requires:	scl-utils
Requires:	%{scl_v8}
Requires:	%{?scl_prefix}mongodb-server
BuildRequires:	scl-utils-build, help2man
BuildRequires:  rh-java-common-javapackages-tools
BuildRequires:	maven30-scldevel
BuildRequires:	rh-java-common-scldevel

%description
This is the main package for %{scl} Software Collection, which installs
necessary packages to use MongoDB %{version_major}.%{version_minor} server.
Software Collections allow to install more versions of the same package
by using alternative directory structure.
Install this package if you want to use MongoDB %{version_major}.%{version_minor}
server on your system

%package runtime
Summary:	Package that handles %{scl} Software Collection.
Group:		Applications/File
Requires:	scl-utils
Requires:	/usr/bin/scl_source
Requires:	%{scl_v8_prefix}runtime
# Those two java common requires are for build-classpath et. al.
# to work. See RHBZ#1129287
Requires:       %{?scl_prefix_java_common}runtime
Requires:       %{?scl_prefix_java_common}javapackages-tools
Requires(post):	policycoreutils-python, libselinux-utils

%description runtime
Package shipping essential scripts to work with %{scl} Software Collection.

%package build
Summary:	Package shipping basic build configuration
Requires:	scl-utils-build
Requires:	%{name}-scldevel = %{version}
Requires:	%{scl_v8_prefix}scldevel
Requires:	%{scl_prefix}scldevel
Group:		Applications/File

%description build
Package shipping essential configuration macros to build
%scl Software Collection.

%package scldevel
Summary:	Package shipping development files for %{scl}.
Group:		Applications/File
Requires:       %{name}-runtime = %{version}
Requires:       maven30-scldevel

%description scldevel
Development files for %{scl} (useful e.g. for hierarchical collection
building with transitive dependencies).

%prep
%setup -c -T

# java.conf
cat <<EOF | tee java.conf
# Java configuration file for %{scl} software collection.
JAVA_LIBDIR=%{_javadir}
JNI_LIBDIR=%{_jnidir}
JVM_ROOT=%{_jvmdir}
EOF

# _scl_root is used without leading slash several times
ROOT_NOSLASH="%{?_scl_root}"
export ROOT_NOSLASH=${ROOT_NOSLASH:1}

# XMvn config
cat <<EOF >configuration.xml
<!-- XMvn configuration file for %{scl} software collection -->
<configuration>
  <resolverSettings>
    <metadataRepositories>
      <repository>%{?_scl_root}/usr/share/maven-metadata</repository>
    </metadataRepositories>
    <prefixes>
      <prefix>%{?_scl_root}</prefix>
    </prefixes>
  </resolverSettings>
  <installerSettings>
    <metadataDir>${ROOT_NOSLASH}/usr/share/maven-metadata</metadataDir>
  </installerSettings>
  <repositories>
    <repository>
      <id>resolve-%{scl}</id>
      <type>compound</type>
      <properties>
        <prefix>${ROOT_NOSLASH}</prefix>
        <namespace>%{scl}</namespace>
      </properties>
      <configuration>
        <repositories>
          <repository>base-resolve</repository>
        </repositories>
      </configuration>
    </repository>
    <repository>
      <id>resolve</id>
      <type>compound</type>
      <configuration>
        <repositories>
        <!-- The %{scl} collection resolves from:
                    1. local repository
                    2. %{scl}
                    3. maven
               collections. -->
          <repository>resolve-local</repository>
          <repository>resolve-%{?scl}</repository>
          <repository>resolve-%{?scl_maven}</repository>
        </repositories>
      </configuration>
    </repository>
    <repository>
      <id>install</id>
      <type>compound</type>
      <properties>
        <prefix>${ROOT_NOSLASH}</prefix>
        <namespace>%{scl}</namespace>
      </properties>
      <configuration>
        <repositories>
          <repository>base-install</repository>
        </repositories>
      </configuration>
    </repository>
  </repositories>
</configuration>
EOF

#=====================#
# Javapackages config #
#=====================#
cat <<EOF | tee javapackages-config.json
{
    "maven.req": {
	"always_generate": [
	    "%{scl}-runtime"
	],
	"java_requires": {
	    "package_name": "java",
	    "always_generate": true,
	    "skip": false
	},
	"java_devel_requires": {
	    "package_name": "java-devel",
	    "always_generate": false,
	    "skip": false
	}
    },
    "javadoc.req": {
	"always_generate": [
	    "%{scl}-runtime"
	]
    }
}
EOF

# This section generates README file from a template and creates man page
# from that file, expanding RPM macros in the template file.
cat <<'EOF' | tee README
%{expand:%(cat %{SOURCE0})}
EOF

# copy the license file so %%files section sees it
cp %{SOURCE1} .

%build
# temporary helper script used by help2man
cat <<\EOF | tee h2m_helper
#!/bin/sh
if [ "$1" = "--version" ]; then
  printf '%%s' "%{?scl_name} %{version} Software Collection"
else
  cat README
fi
EOF
chmod a+x h2m_helper
# generate the man page
help2man -N --section 7 ./h2m_helper -o %{?scl_name}.7

%install
%{?scl_install}

# create enable scriptlet that sets correct environment for collection
cat << EOF | tee -a %{buildroot}%{?_scl_scripts}/enable
. scl_source enable %{scl_v8} %{scl_java_common}
# For binaries
export PATH="%{_bindir}\${PATH:+:\${PATH}}"
# For header files
export CPATH="%{_includedir}\${CPATH:+:\${CPATH}}"
# For libraries during build
export LIBRARY_PATH="%{_libdir}\${LIBRARY_PATH:+:\${LIBRARY_PATH}}"
# For libraries during linking
export LD_LIBRARY_PATH="%{_libdir}\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}"
# For man pages; empty field makes man to consider also standard path
export MANPATH="%{_mandir}:\${MANPATH}"
# For Java Packages Tools to locate java.conf
export JAVACONFDIRS="%{_sysconfdir}/java:\${JAVACONFDIRS:-/etc/java}"
# For XMvn to locate its configuration file(s)
export XDG_CONFIG_DIRS="%{_sysconfdir}/xdg:\${XDG_CONFIG_DIRS:-/etc/xdg}"
# For systemtap
export XDG_DATA_DIRS="%{_datadir}:\${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
# For pkg-config
export PKG_CONFIG_PATH="%{_libdir}/pkgconfig\${PKG_CONFIG_PATH:+:\${PKG_CONFIG_PATH}}"
# For Java RPM generators
export PYTHONPATH="%{_scl_root}%{python_sitearch}:%{_scl_root}%{python_sitelib}\${PYTHONPATH:+:}\${PYTHONPATH:-}"
EOF

# generate service-environment file for mongo[ds] configuration
cat >> %{buildroot}%{_scl_scripts}/service-environment << EOF
# Services are started in a fresh environment without any influence of user's
# environment (like environment variable values). As a consequence,
# information of all enabled collections will be lost during service start up.
# If user needs to run a service under any software collection enabled, this
# collection has to be written into %{scl_upper}_SCLS_ENABLED variable in
# /opt/rh/sclname/service-environment.
%{scl_upper}_SCLS_ENABLED='%{scl}'
EOF

install -d -m 755           %{buildroot}%{_sysconfdir}/java
install -p -m 644 java.conf %{buildroot}%{_sysconfdir}/java/
install -p -m 644 javapackages-config.json %{buildroot}%{_sysconfdir}/java/

install -d -m 755                   %{buildroot}%{_sysconfdir}/xdg/xmvn
install -p -m 644 configuration.xml %{buildroot}%{_sysconfdir}/xdg/xmvn/

# Create java/maven directories so that they'll get properly owned.
# These are listed in the scl_files macro. See also: RHBZ#1057169
install -d -m 755 %{buildroot}%{_javadir}
install -d -m 755 %{buildroot}%{_prefix}/lib/java
install -d -m 755 %{buildroot}%{_javadocdir}
install -d -m 755 %{buildroot}%{_mavenpomdir}
install -d -m 755 %{buildroot}%{_datadir}/maven-effective-poms
install -d -m 755 %{buildroot}%{_mavendepmapfragdir}

# install generated man page
install -d -m 755               %{buildroot}%{_mandir}/man7
install -p -m 644 %{?scl_name}.7 %{buildroot}%{_mandir}/man7/

# create directory for license
install -d -m 755 %{buildroot}%{_licensedir}

# generate rpm macros file for depended collections
cat << EOF | tee -a %{buildroot}%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel
%%scl_%{scl_name_base} %{?scl}
%%scl_prefix_%{scl_name_base} %{?scl_prefix}
EOF


%post runtime
# Simple copy of context from system root to SCL root.
# In case new version needs some additional rules or context definition,
# it needs to be solved by changing selinux-policy.
semanage fcontext -a -e / %{?_scl_root} >/dev/null 2>&1 || :
semanage fcontext -a -e %{_root_sysconfdir} %{_sysconfdir} >/dev/null 2>&1 || :
semanage fcontext -a -e %{_root_localstatedir} %{_localstatedir} >/dev/null 2>&1 || :
selinuxenabled && load_policy || :
restorecon -R %{?_scl_root} >/dev/null 2>&1 || :
restorecon -R %{_sysconfdir} >/dev/null 2>&1 || :
restorecon -R %{_localstatedir} >/dev/null 2>&1 || :


%files

%if 0%{?rhel} >= 7 || 0%{?fedora} >= 15
%files runtime -f filesystem
%license LICENSE
%dir %attr(0755, root, root) %{_sysconfdir}/java/
%dir %attr(0755, root, root) %{_licensedir}/
%dir %attr(0755, root, root) %{_javadir}
%dir %attr(0755, root, root) %{_mavenpomdir}
%else
%files runtime
%doc LICENSE
%endif
%doc README
%{?scl_files}
%config(noreplace) %{_scl_scripts}/service-environment
%config(noreplace) %{_sysconfdir}/java/java.conf
%config(noreplace) %{_sysconfdir}/xdg/xmvn/configuration.xml
%config(noreplace) %{_sysconfdir}/java/javapackages-config.json
%{_mandir}/man7/%{?scl_name}.*

%files build
%doc LICENSE
%{_root_sysconfdir}/rpm/macros.%{scl}-config

%files scldevel
%doc LICENSE
%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel

%changelog
* Mon Jan 11 2016 Marek Skalicky <mskalick@redhat.com> - 2.2-2
- Fixed PYTHONPATH to include also pythonarch directory

* Thu Mar 19 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-19
- Fixed java and maven directory ownership

* Wed Mar 18 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-18
- Use license instead of doc (used by mongodb)
- Fixed rhel7 runtime {_licensedir} directory ownership

* Mon Mar 2 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-17
- Fixed rhel7 runtime {_sysconfdir}/java/ directory ownership

* Fri Feb 27 2015 Honza Horak <hhorak@redhat.com> - 2.0-16
- Remove NFS register feature for questionable usage for DBs

* Mon Jan 26 2015 Honza Horak <hhorak@redhat.com> - 2.0-15
- Fix upper format of scl name

* Mon Jan 26 2015 Honza Horak <hhorak@redhat.com> - 2.0-14
- Create correct directory under register.content

* Mon Jan 26 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-13
- Fixed runtime subpackage file section

* Mon Jan 26 2015 Honza Horak <hhorak@redhat.com> - 2.0-12
- Do not set selinux context  scl root during scl register

* Mon Jan 26 2015 Honza Horak <hhorak@redhat.com> - 2.0-11
- Use cat for README expansion, rather than include macro

* Fri Jan 23 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-10
- Added service-environment into mongodb package
- Fixed runtime directory ownership

* Thu Jan 22 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-9
- Merged origin/rhscl-2.0-rh-mongodb26-rhel-7 (2.0-9)

* Wed Jan 21 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-8
- Moved SCL python27 dependency into rh-mongodb26-mongodb

* Tue Jan 20 2015 Marek Skalicky <mskalick@redhat.com> - 2.0-7
- Added SCL python27 dependency

* Sat Jan 17 2015 Honza Horak <hhorak@redhat.com> - 2.0-6
- Initial register implementation

* Wed Jan 14 2015 Severin Gehwolf <sgehwolf@redhat.com> - 2.0-5
- Update java/maven configuration for thermostat consumption.

* Tue Jan 13 2015 Honza Horak <hhorak@redhat.com> - 2.0-4
- Implement some new scl-utils features and use more scl macros

* Mon Nov 24 2014 Marek Skalicky <mskalic@redhat.com> 2.0-3
- Modified files section to correctly uninstall SCL root

* Tue Nov 18 2014 Marek Skalicky <mskalic@redhat.com> 2.0-2
- Changed and cleaned up requirements

* Fri Nov 14 2014 Marek Skalicky <mskalic@redhat.com> 2.0-1
- added SCL v8 dependency
- changed version for SCL 2.0

* Fri Nov 07 2014 Marek Skalicky <mskalic@redhat.com> 1-2
- removed SCL v8 dependency

* Thu Oct 30 2014 Marek Skalicky <mskalic@redhat.com> 1-1
- initial packaging (based on mongodb24 SCL)

