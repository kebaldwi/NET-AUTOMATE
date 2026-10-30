# Advanced Templating [![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/kebaldwi/DNAC-TEMPLATES)

## Overview

This module is designed to be used after first completing modules in this lab and has been created to address how to use some advanced automation concepts not previously touched on in the previous labs. This enablement type lab is designed to help customers reach beyond what they currently understand, try new concepts, and push the boundaries of automation.

We will cover various topics about template logic to solve multiple use cases during this lab. Some of these concepts have been previously covered but perhaps not in-depth.

The examples shown below can be used in building your versions of the templates. The concept of this lab is for you to create regular templates that you can substitute into the composite to test with. Various methods for the varying use cases will explain the pros and cons along the way. Expand your capabilities with this lab and take your abilities to the next level. You're only inhibited by your imagination. 

## General Information

As previously discussed, Catalyst Center can be used for Plug-and-Play and Day N or Ongoing Templates. Customers will start by building out an Onboarding Template which typically deploys only enough information to bring the device up initially. While it might include the entire configuration for a traditional network device, this is better served by Day N Templates and, for more flexibility Composite Templates. They can apply ongoing changes and allow device modifications after initial deployment. 

Another important consideration is that part of a typical configuration would include some lines of code, which will be automatically built out using the information within the *Design >Network Settings >* application within Catalyst Center. If the Design component is used, you should **not** deploy the same feature from cli code in a template to configure the device. It's a decision you have to make upfront, avoids a lot of lines in the templates, and allows for a more UI-centric configuration that is easier to maintain. 

As guidance, try and use **Design Settings** for as many of the configurations as you can, leaving Templates light and nimble for configurations that might change ongoing.

We will cover various aspects and use cases that perhaps allow for a more programmatic approach with these things in mind.

## Topics

The various topics covered in the lab will be the following:

1. *Self-deleting EEM scripts*
2. Working with *Arrays and Methods* in *Velocity*
3. Using *Conditional Statements* for Configuration
4. Velocity and *Enable* versus *Interactive* mode
5. Assigning port configuration in a stack
6. Autoconf vs Smartports
7. IBNS 2.0 configuration

## Use Cases

The Topics listed above will be covered in several use cases to show the capability and flexibility of the templating engine within Catalyst Center. While we will utilize Velocity language, the same can be accomplished in the Jinja2 language.

1. [Renaming interfaces](./AdvancedTemplating.md#step-1---renaming-interfaces---use-case)
2. [Building Stacks](./AdvancedTemplating.md#step-2---building-stacks---use-case)
3. [Building VLAN configuration](./AdvancedTemplating.md#step-3---building-vlan-databases---use-case)
4. [Assigning port configuration](./AdvancedTemplating.md#step-4---assigning-port-configuration---use-case)
5. [Autoconf port configuration](./AdvancedTemplating.md#step-5---autoconf-port-configuration---use-case)
6. [IBNS 2.0 Port Configuration](./AdvancedTemplating.md#step-6---ibns20-port-configuration---use-case)

## Step 1 - ***Renaming Interfaces - Use Case***

Previously within the DayN Module, we introduced a methodology of automatically naming the interfaces within the switch. When a new device or switch/router/access point connects to a switch, we want to describe those interfaces. Naming the uplinks specifically and the various wireless access points and IP Phones would be an excellent addition. 

<details open>
<summary> Click for Details and Sub Tasks</summary>

### ***Examine Code***

This script will rename the uplinks connected to a AP, Phone, Router or Switch , it is limited in terms of the following:

1. Timing, as it's not scheduled, and you cannot clear the CDP table from the template
2. Naming 3rd party devices is also not taken into consideration via LLDP

```J2
   {#- Automated Uplink Description Script -#}
   {#- This will always ensure the uplink descriptions are correct to upstream -#}
   {#- Switches within the infrastructure  -#}
    event manager applet update-port authorization bypass
     event neighbor-discovery interface regexp GigabitEthernet.* cdp add
     action 101 regexp "(Switch|Router)" "$_nd_cdp_capabilities_string"
     action 200 if $_regexp_result eq "1"
     action 201  regexp "(Trans-Bridge)" "$_nd_cdp_capabilities_string"
     action 210  if $_regexp_result eq "1"
     action 211   cli command "enable"
     action 212   cli command "config t"
     action 213   cli command "interface $_nd_local_intf_name"
     action 214   regexp "^([^\.]+)" "$_nd_cdp_entry_name" match host
     action 215   regexp "^([^\.]+)" "$_nd_port_id" match connectedport
     action 216   cli command "no description"
     action 217   cli command "description AP - $host - $connectedport"
     action 220  else
     action 221   cli command "enable"
     action 222   cli command "config t"
     action 223   cli command "interface $_nd_local_intf_name"
     action 224   regexp "^([^\.]+)\." "$_nd_cdp_entry_name" match host
     action 225   regexp "^([^\.]+)" "$_nd_port_id" match connectedport
     action 226   cli command "no description"
     action 227   cli command "description Link - $host - $connectedport"
     action 240  end
     action 250 else
     action 251  regexp "(Phone)" "$_nd_cdp_capabilities_string"
     action 252  if $_regexp_result eq "1"
     action 253   cli command "enable"
     action 254   cli command "config t"
     action 255   cli command "interface $_nd_local_intf_name"
     action 256   regexp "^([^\.]+)" "$_nd_cdp_entry_name" match host
     action 257   regexp "^([^\.]+)" "$_nd_port_id" match connectedport
     action 258   cli command "no description"
     action 259   cli command "description Phone - $host - $connectedport"
     action 260  end
     action 270 end
     action 280 cli command "write"
```

You will see that lines *201 to 220* were added to the EEM script. We look for the keyword `Trans-Bridge` within the built-in variable to determine if the port is connected to an Access Point within that section. It results in a True or binary 1 state, and the included code from lines *211 to 220* runs line by line. The configuration adds a description to the interface for the phone of `description AP - KO-AP0C75 - GigabitEthernet0`, for example.

You will see that lines *250 to 260* were added to the EEM script. We look for the keyword `Phone` within the built-in variable to determine if the port is connected to a Phone within that section. It results in a True or binary 1 state, and the included code from lines *253 to 260* runs line by line. For example, the configuration adds a description to the interface for the phone of `description Phone - SEPB07D47D34910 - Port 1`.

While we can get the configuration in place, it will only run when the port is cycled or when the CDP information for the port is cleared. Therefore, to solve the problem, we employ a *Self-Destructing EEM script*.

*Self-Destructing EEM scripts* are those that delete themselves on termination. Within the code below, you will notice that line 2.1 removes the EEM applet from the configuration, and then line 2.3 ensures the configuration is written to NVRAM before terminating.

```J2
   event manager applet POST_PNP authorization bypass
    event timer countdown time 30
    action 1.0 cli command "enable"
    action 1.1 cli command "clear cdp table"
    action 2.0 cli command "config t"
    action 2.1 cli command "no event manager applet POST_PNP"
    action 2.2 cli command "end"
    action 2.3 cli command "wr"
```

This code allows us to *clear the CDP table* and delete itself but leave the other EEM script on the switch for any moves, adds, and changes to the devices connected to the switch.

The code above could be augmented with logic for LLDP to be added should the need arise.

</details>

## Step 2 - ***Building Stacks - Use Case***

Previously within the DayN Module, we introduced a methodology of automatically building a data stack and power stack configuration within the switch. When a new device or switch is built, we may want to control which switch is Active and standby within the stack. 

<details open>
<summary> Click for Details and Sub Tasks</summary>

### ***Examine Code***

To that end, the following configuration has been built previously:
[//]: # ({% raw %})
```J2
   {#- 9300 Stack Power and 9300, 9200 Priority -#}
   {% set StackCount = __device.platformId | split(",")  %}
   {% set StackMemberCount =  StackCount | length  -%}
   
   {% if StackMemberCount > 1 && ("C93" in __device.platformId || "C92" in __device.platformId) %}
     {% if "C93" in __device.platformId %}
        stack-power stack Powerstack1
        mode redundant strict
        {% if StackMemberCount > 4 %}
           stack-power stack Powerstack2
           mode redundant strict
        {% endif %}
        {% for Switch in range(0,StackMemberCount,1) %}
           stack-power switch {{ loop.index }}
           {% if loop.index <= (StackMemberCount/2|round('ceil')) or StackMemberCount < 5 %}
              stack Powerstack1
           {% elif loop.index > (StackMemberCount/2|round('ceil')) %}
              stack Powerstack2
           {% endif %}
        {% endfor %}
     {% endif %}
     #MODE_ENABLE
     {% for Switch in range(0,StackMemberCount,1) %}
       {% if loop.index == 1 %}
          switch {{ loop.index }} priority 10
       {% elif loop.index == 2 %}
          switch {{ loop.index }} priority 9
       {% else %}
          switch {{ loop.index }} priority 8
       {% endif %}
     {% endfor %}
     #MODE_END_ENABLE
   {% endif %}
```
[//]: # ({% endraw %})

Within this script, you can see the Arrays `Stackcount` formed using the `.split(",")` method, which takes the string returned from the database and splits the list into two elements within the Array `Stackcount`. You could address each element in the Array, remembering that Arrays always start the numbering of elements at position zero (0). You could call the data with these two options; for the first element in the Array `Stackcount[0]` or the second element in the Array `Stackcount[1]`. Here we store the length of the array or the number of switches in a variable `StackMemberCount`.

Within this script, you can see the Conditional Statements `if elif else endif`. These are used to dynamically build configuration for switch stacks no matter how many switches are within the stack. For example, if the number of switches in the stack exceeds 4, it automatically creates 2 powerstack environments for power redundancy. The script also prioritizes the Active and Standby switch above those of the rest of the switches in the stack. Lets examine in more depth:

1. The code will run only if the number of switches in the stack is found to be greater than 1. This means that stackpower is only configured on stacks of two or more switches. 

[//]: # ({% raw %})
```j2
   {% if StackMemberCount > 1 %}
```
[//]: # ({% endraw %})

2. The next step is to correctly set the number of powerstack required. If the number of switches exceeds 4 then we need two powerstacks set up.

```j2
   stack-power stack Powerstack1
   mode redundant strict
   {% if StackMemberCount > 4 %}
      stack-power stack Powerstack2
      mode redundant strict
   {% endif %}
```

3. The next step is to iterate through the switches in the stack setting the stackpower appropriately for each switch and adding them to the correct powerstack 

[//]: # ({% raw %})
```j2
   {% for Switch in range(0,StackMemberCount,1) %}
      {% if loop.index <= (StackMemberCount/2|round('ceil')) %}
         stack-power switch {{ loop.index }}
         stack Powerstack1
      {% elif loop.index > (StackMemberCount/2|round('ceil')) %}
         stack-power switch {{ loop.index }}
         stack Powerstack2
      {% endif %}
      {{ loop.index }}
   {% endfor %}
```

4. Lastly, we will set the switch priority appropriately on each switch for master and standby, and then for the remaining switches within the stack so that switch numbering matches the priority levels.

```j2
   {% for Switch in range(0,StackMemberCount,1) %}
      {% if loop.index == 1 %}
         switch {{ loop.index }} priority 10
      {% elif Switch == 2 %}
         switch {{ loop.index }} priority 9
      {% else %}
         switch {{ loop.index }} priority 8
      {% endif %}
   {% endfor %}
```
[//]: # ({% endraw %})

Within this script, you can see the use of the Enable Statements `#MODE_ENABLE #MODE_END_ENABLE`. These commands allow for enable level configuration commands to be entered. This script needs to configure the enable level command to set switch priority for individual switches `switch {{loop.index}} priority #`. Bracketing this configuration command with the velocity statements `#MODE_ENABLE #MODE_END_ENABLE` allows us to change from configuration mode to enable mode and back again.

</details>

## Step 3 - ***Building Vlan Databases - Use Case***

Previously within the DayN Module, we introduced a methodology of automatically building a vlan database within the configuration of the switch. When a new device or switch is built, we may want to control which the vlans within the stack. 

The **macros** that are called to build vlans from included regular templates. Think of these similarly to **Python** functions where we in parenthesis parse a list of variables for use in the function. In this list we see `vlanarray[x]` which is calling elements of a vlan list like `[10,20,30,40]`. This list was populated when we created the vlan database and stored it in this array. 

<details open>
<summary> Click for Details and Sub Tasks</summary>

### ***Examine Code***

[//]: # ({% raw %})
```J2
   {# Dictionaries of VLANS per Site #}
   {% set SiteAvlans = [
     {'vlan':'5','name':'mgmtvlan'},
     {'vlan':'10','name':'apvlan'},
     {'vlan':'20','name':'datavlan'},
     {'vlan':'30','name':'voicevlan'},
     {'vlan':'40','name':'guestvlan'},
     {'vlan':'999','name':'disabledvlan'}
     ]%}
   !
   {# MACRO VLAN DB Dependencies #}
   {% macro configure_vlans(vlanpairs)  %}
     {% for vlanpair in vlanpairs %}
       vlan {{ vlanpair['vlan'] }}
       name {{ vlanpair['name'] }}
     {% endfor %}
   {% endmacro %}
   !
   {# MACRO Vlan Search Function #}
   {% macro search_vlans(vlanpairs) %}
     {#{% set vlanArray = [] %}#}
     {% for vlanpair in vlanpairs %}
       {% if vlanpair['name'] == "apvlan" %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif vlanpair['name'] == "datavlan"%}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif "voice" in vlanpair['name'] %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif "guest" in vlanpair['name'] %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif "disabled" in vlanpair['name'] %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% else %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% endif %}
     {% endfor %}
   {% endmacro %}
```
[//]: # ({% endraw %})

Here you can see a **dictionary** used to hold **key value pairs** in a list for use. When parsed to the **macro** `configure_vlans(vlanpairs)` they build out the **vlan database**, looping through and for every line adding the vlan and the name entry to the configuration. Below that you will see search **macro**, which creates the vlanarray above.

</details>

## Step 4 - ***Assigning Port Configuration - Use Case***

Previously within the DayN Module, we introduced a methodology of automatically configuring the interfaces within the switch. This configuration relied on a few variables used to extrapolate the settings that were then configured via the template. This allowed a set of macros to be utilized to build out the various settings for VLANs, Ports, and Uplinks. 

<details open>
<summary> Click for Details and Sub Tasks</summary>

### ***Examine Code***

We will analyze the configuration in more detail below. Lets look at this intimidating block of code and disect it.
[//]: # ({% raw %})
```J2
   {# System Variable example interfaces in one logical code construct #}
   {# Select and Configure Access Point interfaces#}
   {% set apintlog = uplink_portarray %}
   !
   {% for apinterface in accesspoint_interfaces %}
     {% for interface in __interface %}
       {% if interface.portName in apintlog %}
       {% elif interface.portName == apinterface %}
         default interface {{ interface.portName }}
         interface {{ interface.portName }}
          {{ baseconf_interface() }}
         {% do apintlog.append(interface.portName) %}
       {% endif %}
     {% endfor %}
   {% endfor %}
   !
   {# Automatically Configure Workstation Remaining interfaces#}
   {% for interface in __interface %}
     {% if interface.interfaceType == "Physical" && interface.portName.replaceAll("(^[a-zA-Z]+).*","$1")    == "GigabitEthernet"  %}
       {% if interface.portName.replaceAll("(^[a-zA-Z]+.).*", "$1") != "GigabitEthernet0" %}
         {% if interface.portName.replaceAll("^[a-zA-Z]+(\\d+)/(\\d+)/(\\d+)", "$2") != 1 %}
           {% if interface.portName in apintlog %}
           {% else %}
             default interface {{ interface.portName }}
             interface {{ interface.portName }}
               {{ ibns_baseconf_interface() }}
           {% endif %}
         {% endif %}
       {% endif %}
     {% endif %}
   {% endfor %}
```


In the first block of code we see an array being created `{% set apintlog = uplink_portarray %}`. This array is populated earlier in the template from an interrogation of the number of trunk links connected initially to the switch. The assumption is that no other devices are connected at this time. 


```J2
   {# Determine whether target is Dual or Single Uplink Target #}
   {% set uplink_portarray = [] %}
   {% for interface in __interface %}
     {% if interface.portMode == "trunk" && interface.interfaceType == "Physical" %}
       {% do uplink_portarray.append(interface.portName) %}
     {% endif %}
   {% endfor %}
```


So this is where we get the value for the `uplink_portarray`. As you can see it is a list of portnames of all the ports which are physical trunks. This value is then stored in the `apintlog` variable for use in the next sections.

Next we want to configure some ports for Access Points. To show the use of Autoconf, we are going to use a specific interface template here. Lets see the code:

```J2
  {% for apinterface in accesspoint_interfaces %}
     {% for interface in __interface %}
       {% if interface.portName in apintlog %}
       {% elif interface.portName == apinterface %}
         default interface {{ interface.portName }}
         interface {{ interface.portName }}
          {{ baseconf_interface() }}
         {% do apintlog.append(interface.portName) %}
       {% endif %}
     {% endfor %}
   {% endfor %}
```
[//]: # ({% endraw %})

The first line references a Bind Variable. A Bind Variable is similar to a system variable, but it can be used to select interfaces so please take a look at the variable in the form tool within the Template Hub. So the loop will loop through all interfaces selected in the `accesspoint_interfaces` variable. 

For each loop iteration we will store the target `apinterface` and compare it to those using the following logic. Within all the ports of the switch we will loop through each, and ensure that they are not previously configured using the `apintlog` variable for comparison. 

We will also ensure we only configure those we selected comparing each interface to the `apinterface` selected to see if the target has been found. If it is found, we default the interface and then place a base configuration on it via a interface macro. We finally append the newly configured interface to the `apintlog` array to ensure it is not modified further.

Once all the Access Points are configured we then target the rest of the ports for 802.1x configuration. 

```J2
   {# Automatically Configure Workstation Remaining interfaces#}
   {% for interface in __interface %}
     {% if interface.interfaceType == "Physical" && interface.portName.replaceAll("(^[a-zA-Z]+).*","$1")    == "GigabitEthernet"  %}
       {% if interface.portName.replaceAll("(^[a-zA-Z]+.).*", "$1") != "GigabitEthernet0" %}
         {% if interface.portName.replaceAll("^[a-zA-Z]+(\\d+)/(\\d+)/(\\d+)", "$2") != 1 %}
           {% if interface.portName in apintlog %}
           {% else %}
             default interface {{ interface.portName }}
             interface {{ interface.portName }}
               {{ ibns_baseconf_interface() }}
           {% endif %}
         {% endif %}
       {% endif %}
     {% endif %}
   {% endfor %}
```

We loop through all the interfaces on the switch, ensuring we configuring only those starting with GigabitEthernet and negating the management interface and any that are network modules. We then ensure the interface is not in the `apintlog` array as previously configured, and if all that is true default the interface, and place a 802.1x config on it via an interface macro.

</details>

## Step 5 - ***Autoconf Port Configuration - Use Case***

Previously within the DayN Module, we introduced a methodology of automatically configuring the interfaces within the switch. This configuration relies on a few variables used to extrapolate the settings that were then configured via the template. This allowed a set of macros to be utilized to build out the various settings for VLANs, Ports, and Uplinks. 

In previous code revisions, we could deal with some of the problems with Auto Smart Port technology, but that has been deprecated, and its replacement is a lot more dynamic. This section will deal with the first part of the problem concerning assigning ports for hardware like Access Points.

The Autoconf methodology allows for dynamic and automated configuration of switch interfaces based on predefined templates and VLAN assignments. It is particularly useful in large-scale deployments where manual configuration would be time-consuming and error-prone. Due to its dynamic nature it can adapt to changes in the network environment without requiring extensive manual intervention. To avoid misconfigurations, it is important to ensure that the templates and VLAN assignments are accurately defined and maintained.

As the network environment evolves, the Autoconf methodology ensures that interface configurations remain consistent and aligned with the defined templates, reducing the risk of human error and improving overall network reliability.

> [!WARNING]
> :mega: Due to the dynamic nature, it is crucial that prior to enabling Autoconf globally, that any uplink or statically configured interfaces are configured with `access-session inherit disable autoconf` to prevent unintended automatic configurations on these interfaces.

This Autoconf methodology was deployed via template.

<details open>
<summary> Click for Details and Sub Tasks</summary>

### ***Examine Code***

First, lets take a look at the code which causes everything to happen for autoconf

[//]: # ({% raw %})
```J2
   {{ autoconf_accesspoint(vlanArray[1]) }}
   {{ autoconf_flexaccesspoint(vlanArray[1], vlanArray[2], vlanArray[3], vlanArray[4]) }} 
   {{ autoconf_workstation(vlanArray[2], vlanArray[3]) }}
   {{ autoconf_baseconfig(vlanArray[1]) }}
   !
   {% include "DCLOUD CATC Template Lab DayN Jinja2/AutoConf-Configuration" %}
```

The **macros** that are called build interface templates. Think of these similarly to **Python** functions where we in parenthesis parse a list of variables for use in the function. In this list we see `vlanarray[x]` which is calling elements of a vlan list like `[10,20,30,40]`. This list was populated when we created the vlan database and stored it in this array. 

```J2
   {# Dictionaries of VLANS per Site #}
   {% set SiteAvlans = [
     {'vlan':'5','name':'mgmtvlan'},
     {'vlan':'10','name':'apvlan'},
     {'vlan':'20','name':'datavlan'},
     {'vlan':'30','name':'voicevlan'},
     {'vlan':'40','name':'guestvlan'},
     {'vlan':'999','name':'disabledvlan'}
     ]%}
   !
   {# MACRO Vlan Search Function #}
   {% macro search_vlans(vlanpairs) %}
     {#{% set vlanArray = [] %}#}
     {% for vlanpair in vlanpairs %}
       {% if vlanpair['name'] == "apvlan" %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif vlanpair['name'] == "datavlan"%}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif "voice" in vlanpair['name'] %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif "guest" in vlanpair['name'] %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% elif "disabled" in vlanpair['name'] %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% else %}
         {% do vlanArray.append(vlanpair['vlan']) %}
       {% endif %}
     {% endfor %}
   {% endmacro %}
```
[//]: # ({% endraw %})

Here you can see a **dictionary** used to hold **key value pairs** in a list for use. When parsed to the **macro** `configure_vlans(vlanpairs)` they build out the **vlan database**, looping through and for every line adding the vlan and the name entry to the configuration. Below that you will see search **macro**, which creates the vlanarray above.

This is utilized in conjunction with the **macros**, which build out the interface templates we will use later.

```J2
   {{ autoconf_accesspoint(vlanArray[1]) }}
   {{ autoconf_flexaccesspoint(vlanArray[1], vlanArray[2], vlanArray[3], vlanArray[4]) }} 
   {{ autoconf_workstation(vlanArray[2], vlanArray[3]) }}
   {{ autoconf_baseconfig(vlanArray[1]) }}
```

They **macros** are as follows

[//]: # ({% raw %})
```J2
   {# AutoConf Macro Section #}
   {# AutoConf Base Configuration Macro #}
   {% macro baseconf_interface() %}
        switchport mode access
        snmp trap mac-notification change added
        snmp trap mac-notification change removed
        source template BASE_AUTOCONF
   {% endmacro %}
   !
   {# Interface Access Point Template to be used with Autoconf for AP's #}
   {% macro autoconf_accesspoint(vlan_number) %} 
     template ACCESS_POINT
      description Access Point Interface
      switchport access vlan {{ vlan_number }}
      switchport mode access
      spanning-tree portfast
   {% endmacro %}
   !
   {# Interface FLex-Access Point Template to be used with Autoconf for Flex AP's #}
   {% macro autoconf_flexaccesspoint(vlan_number, data_number, voice_number, guest_number) %} 
     template FLEX_ACCESS_POINT
      description Flex Access Point Interface
      switchport mode trunk
      switchport trunk native vlan {{ vlan_number }}
      switchport trunk allowed vlan {{ vlan_number }},{{ data_number}},{{ voice_number}},{{ guest_number }}
      spanning-tree portfast trunk
   {% endmacro %}
   !
   {# Interface Workstation Template to be used with Autoconf for AP's #}
   {% macro autoconf_workstation(vlan_number, voice_number) %} 
     template WORKSTATION
      description Workstation Interface
      switchport access vlan {{ vlan_number }}
      switchport voice vlan {{ voice_number }}
      switchport mode access
      spanning-tree portfast
   {% endmacro %}
   !
   {# Interface Base Configuration Template to be used with Autoconf for baseconfig's #}
   {% macro autoconf_baseconfig(vlan_number) %} 
     template BASE_AUTOCONF
      description Base Config
      switchport access vlan {{ vlan_number }}
      switchport mode access
      spanning-tree portfast
   {% endmacro %}
```
[//]: # ({% endraw %})

> [!WARNING]
> :mega: Due to the dynamic nature, it is crucial that prior to enabling Autoconf globally, that any uplink or statically configured interfaces are configured with `access-session inherit disable autoconf` to prevent unintended automatic configurations on these interfaces.

Next, we need to set up the macros, but we will make use of **Autoconf** and the **Templates** above. **Autoconf** is a solution that can be used to manage port configurations for data or voice VLAN, quality of service (QoS) parameters, storm control, and MAC-based port security on end devices that are deployed in the access layer of a network. Device classification is enabled when you enable the Autoconf feature using the `autoconf enable` command in global configuration mode. The device detection acts as an event trigger, which applies the appropriate automatic template to the interface. When the Autoconf feature is enabled using the autoconf enable command, the default Autoconf service policy is applied to all the interfaces. For more information about **[Autoconf](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9400/software/release/16-12/configuration_guide/nmgmt/b_1612_nmgmt_9400_cg/configuring_autoconf.pdf)** or alternatively [Autoconf](../../CODE/DOCS/configuring_autoconf.pdf)

```J2
   {# AutoConf Configurations #}
   !
   {# Enabling Autoconf on switch with interactive command #}
   #INTERACTIVE
   autoconf enable<IQ>yes<R>y
   #END_INTERACTIVE 
   !
   {# Augmenting existing hidden parameter map with modifications #}
   parameter-map type subscriber attribute-to-service BUILTIN_DEVICE_TO_TEMPLATE
    10 map device-type regex "Cisco-IP-Phone"
     20 interface-template WORKSTATION
    20 map device-type regex "Cisco-IP-Camera"
     20 interface-template WORKSTATION
    30 map device-type regex "Cisco-DMP"
     20 interface-template WORKSTATION
    40 map oui eq "00.0f.44"
     20 interface-template WORKSTATION
    50 map oui eq "00.23.ac"
     20 interface-template WORKSTATION
    60 map device-type regex "Cisco-AIR-AP"
     20 interface-template FLEX_ACCESS_POINT
    70 map device-type regex "Cisco-AIR-LAP"
     20 interface-template FLEX_ACCESS_POINT
    80 map device-type regex "Cisco-TelePresence"
     20 interface-template WORKSTATION
    90 map device-type regex "Surveillance-Camera"
     10 interface-template WORKSTATION
    100 map device-type regex "Video-Conference"
     10 interface-template WORKSTATION
    110 map device-type regex "Cisco-CAT-LAP"
     10 interface-template FLEX_ACCESS_POINT
    120 map oui eq "00.24.9b"
     10 interface-template WORKSTATION 
   !
```

So the command `autoconf` enables the device classifier, which can then be manipulated to stray from the built-in templates through a **parameter-map**. The parameter map command allows for the mapping of defined interface templates. This is what we need to create our template for the Access Point. The **macro** `FLEX_ACCESS_POINT` will be used to configure the interfaces delivering the source template for those selected as Access Point when the onboard device classifier sees a device of the profile `Cisco-CAT-LAP`.

This will configure the interface with the commands listed. When a device is plugged in, the device classifier will run. The interface will by default use the derived configuration of the `BASE_AUTOCONF` interface template, but should an Access Point be plugged in; then the interface would dynammically logically assign the `FLEX_ACCESS_POINT` template. 

Delivering the code to the interfaces becomes simpler now because we utilize a more dynamic device classification approach. 

We will also ensure we only configure those we selected comparing each interface to the `apinterface` selected to see if the target has been found. If it is found, we default the interface and then place a base configuration on it via a interface macro. We finally append the newly configured interface to the `apintlog` array to ensure it is not modified further.

Once all the Access Points interfaces are configured we then target the rest of the ports for 802.1x configuration. 

[//]: # ({% raw %})
```J2
   {% for apinterface in accesspoint_interfaces %}
     {% for interface in __interface %}
       {% if interface.portName in apintlog %}
       {% elif interface.portName == apinterface %}
         default interface {{ interface.portName }}
         interface {{ interface.portName }}
          {{ baseconf_interface() }}
         {% do apintlog.append(interface.portName) %}
       {% endif %}
     {% endfor %}
   {% endfor %}
```
[//]: # ({% endraw %})

We loop through all the interfaces on the switch, ensuring we configuring only those starting with GigabitEthernet and negating the management interface and any that are network modules. We then ensure the interface is not in the `apintlog` array as previously configured, and if all that is true default the interface, and place a autoconf config on it via an interface macro.

</details>

## Step 6 - ***IBNS2.0 Port Configuration - Use Case***

Previously within the DayN Module, we also deployed configuration on the bulk of interfaces using **IBNS2.0** and how to deal with host onboarding in a Non **SDAccess** Fabric environment. Once the Identity Services Engine is integrated with Catalyst Center, then not only do you get the benefit of **pxgrid** integration allowing for the building of policy, but the AAA Server section within Design will build out the various settings which inturn program the network access devices for AAA Network and Client Dot1x settings.

> [!IMPORTANT] 
> It is also essential to understand that with **IBNS2.0** and interface templates or statically configured interfaces running in **closed mode**, the dynamic capability of **Autoconf** will **not** operate because there is a service-policy applied to the interface. Additionally, remember in closed mode no packets are forwarded including DHCP prior to authentication occurring.

Previously we introduced a methodology of automatically configuring the interfaces within the switch. This configuration relies on a few variables used to extrapolate the settings that were then configured via the regular template. This used a set of macros to be utilized to build out the various settings for VLANs, Ports, and Uplinks. 

So lets take a look at the configuration we will deploy:

<details open>
<summary> Click for Details and Sub Tasks</summary>

### ***Examine Code***

We will need to build a set of policies for **Open**, **Closed** and **Low-Impact** mode. These are deployed as a static list and can be maintained in a regular template. These policies and classifications are required but not automatically deployed by Catalyst Center's integrated deployment.

[//]: # ({% raw %})
```J2
  {# IBNS configurations build #}
  !
  {# Classifications #}
  class-map type control subscriber match-all AAA_SVR_DOWN_AUTHD_HOST
   match authorization-status authorized
   match result-type aaa-timeout
  !
  class-map type control subscriber match-all AAA_SVR_DOWN_UNAUTHD_HOST
   match authorization-status unauthorized
   match result-type aaa-timeout
  !
  class-map type control subscriber match-all AUTHC_SUCCESS-AUTHZ_FAIL
   match authorization-status unauthorized
   match result-type success
  !
  class-map type control subscriber match-all DOT1X
   match method dot1x
  !
  class-map type control subscriber match-all DOT1X_FAILED
   match method dot1x
   match result-type method dot1x authoritative
  !
  class-map type control subscriber match-all DOT1X_MEDIUM_PRIO
   match authorizing-method-priority gt 20
  !
  class-map type control subscriber match-all DOT1X_NO_RESP
   match method dot1x
   match result-type method dot1x agent-not-found
  !
  class-map type control subscriber match-all DOT1X_TIMEOUT
   match method dot1x
   match result-type method dot1x method-timeout
  !
  class-map type control subscriber match-any IN_CRITICAL_AUTH
   match activated-service-template DefaultCriticalVoice_SRV_TEMPLATE
  !
  class-map type control subscriber match-any IN_CRITICAL_AUTH_CLOSED_MODE
   match activated-service-template DefaultCriticalAuthVlan_SRV_TEMPLATE
   match activated-service-template DefaultCriticalVoice_SRV_TEMPLATE
  !
  class-map type control subscriber match-all MAB
   match method mab
  !
  class-map type control subscriber match-all MAB_FAILED
   match method mab
   match result-type method mab authoritative
  !
  class-map type control subscriber match-none NOT_IN_CRITICAL_AUTH
   match activated-service-template DefaultCriticalVoice_SRV_TEMPLATE
  !
  class-map type control subscriber match-none NOT_IN_CRITICAL_AUTH_CLOSED_MODE
   match activated-service-template DefaultCriticalAuthVlan_SRV_TEMPLATE
   match activated-service-template DefaultCriticalVoice_SRV_TEMPLATE
  !
  {# Policy Maps #}
  {# CLOSED 1X then MAB Template #}
  policy-map type control subscriber PMAP_DefaultWiredDot1xClosedAuth_1X_MAB
   event session-started match-all
    10 class always do-until-failure
     10 authenticate using dot1x retries 2 retry-time 0 priority 10
   event authentication-failure match-first
    5 class DOT1X_FAILED do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    10 class AAA_SVR_DOWN_UNAUTHD_HOST do-until-failure
     30 authorize
     40 pause reauthentication
    20 class AAA_SVR_DOWN_AUTHD_HOST do-until-failure
     10 pause reauthentication
     20 authorize
    30 class DOT1X_NO_RESP do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    40 class MAB_FAILED do-until-failure
     10 terminate mab
     20 authentication-restart 60
    50 class DOT1X_TIMEOUT do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    60 class always do-until-failure
     10 terminate dot1x
     20 terminate mab
     30 authentication-restart 60
   event aaa-available match-all
    10 class IN_CRITICAL_AUTH_CLOSED_MODE do-until-failure
     10 clear-session
    20 class NOT_IN_CRITICAL_AUTH_CLOSED_MODE do-until-failure
     10 resume reauthentication
   event agent-found match-all
    10 class always do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
   event inactivity-timeout match-all
    10 class always do-until-failure
     10 clear-session
   event authentication-success match-all
   event violation match-all
    10 class always do-until-failure
     10 restrict
   event authorization-failure match-all
    10 class AUTHC_SUCCESS-AUTHZ_FAIL do-until-failure
     10 authentication-restart 60
  !
  {# CLOSED MAB then 1X Template #}
  policy-map type control subscriber PMAP_DefaultWiredDot1xClosedAuth_MAB_1X
   event session-started match-all
    10 class always do-until-failure
     10 authenticate using mab priority 20
   event authentication-failure match-first
    5 class DOT1X_FAILED do-until-failure
     10 terminate dot1x
     20 authentication-restart 60
    10 class AAA_SVR_DOWN_UNAUTHD_HOST do-until-failure
     30 authorize
     40 pause reauthentication
    20 class AAA_SVR_DOWN_AUTHD_HOST do-until-failure
     10 pause reauthentication
     20 authorize
    30 class MAB_FAILED do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
    40 class DOT1X_NO_RESP do-until-failure
     10 terminate dot1x
     20 authentication-restart 60
    50 class DOT1X_TIMEOUT do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    60 class always do-until-failure
     10 terminate mab
     20 terminate dot1x
     30 authentication-restart 60
   event aaa-available match-all
    10 class IN_CRITICAL_AUTH_CLOSED_MODE do-until-failure
     10 clear-session
    20 class NOT_IN_CRITICAL_AUTH_CLOSED_MODE do-until-failure
     10 resume reauthentication
   event agent-found match-all
    10 class always do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
   event inactivity-timeout match-all
    10 class always do-until-failure
     10 clear-session
   event authentication-success match-all
   event violation match-all
    10 class always do-until-failure
     10 restrict
   event authorization-failure match-all
    10 class AUTHC_SUCCESS-AUTHZ_FAIL do-until-failure
     10 authentication-restart 60
  !
  {# LOW IMPACT 1X then MAB Template #}
  policy-map type control subscriber PMAP_DefaultWiredDot1xLowImpactAuth_1X_MAB
   event session-started match-all
    10 class always do-until-failure
     10 authenticate using dot1x retries 2 retry-time 0 priority 10
   event authentication-failure match-first
    5 class DOT1X_FAILED do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    10 class AAA_SVR_DOWN_UNAUTHD_HOST do-until-failure
     25 activate service-template DefaultCriticalAccess_SRV_TEMPLATE
     30 authorize
     40 pause reauthentication
    20 class AAA_SVR_DOWN_AUTHD_HOST do-until-failure
     10 pause reauthentication
     20 authorize
    30 class DOT1X_NO_RESP do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    40 class MAB_FAILED do-until-failure
     10 terminate mab
     20 authentication-restart 60
    50 class DOT1X_TIMEOUT do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    60 class always do-until-failure
     10 terminate dot1x
     20 terminate mab
     30 authentication-restart 60
   event aaa-available match-all
    10 class IN_CRITICAL_AUTH do-until-failure
     10 clear-session
    20 class NOT_IN_CRITICAL_AUTH do-until-failure
     10 resume reauthentication
   event agent-found match-all
    10 class always do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
   event inactivity-timeout match-all
    10 class always do-until-failure
     10 clear-session
   event authentication-success match-all
   event violation match-all
    10 class always do-until-failure
     10 restrict
   event authorization-failure match-all
    10 class AUTHC_SUCCESS-AUTHZ_FAIL do-until-failure
     10 authentication-restart 60
  !
  {# LOW IMPACT MAB then 1X Template #}
  policy-map type control subscriber PMAP_DefaultWiredDot1xLowImpactAuth_MAB_1X
   event session-started match-all
    10 class always do-until-failure
     10 authenticate using mab priority 20
   event authentication-failure match-first
    5 class DOT1X_FAILED do-until-failure
     10 terminate dot1x
     20 authentication-restart 60
    10 class AAA_SVR_DOWN_UNAUTHD_HOST do-until-failure
     25 activate service-template DefaultCriticalAccess_SRV_TEMPLATE
     30 authorize
     40 pause reauthentication
    20 class AAA_SVR_DOWN_AUTHD_HOST do-until-failure
     10 pause reauthentication
     20 authorize
    30 class MAB_FAILED do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
    40 class DOT1X_NO_RESP do-until-failure
     10 terminate dot1x
     20 authentication-restart 60
    50 class DOT1X_TIMEOUT do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    60 class always do-until-failure
     10 terminate mab
     20 terminate dot1x
     30 authentication-restart 60
   event aaa-available match-all
    10 class IN_CRITICAL_AUTH do-until-failure
     10 clear-session
    20 class NOT_IN_CRITICAL_AUTH do-until-failure
     10 resume reauthentication
   event agent-found match-all
    10 class always do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
   event inactivity-timeout match-all
    10 class always do-until-failure
     10 clear-session
   event authentication-success match-all
   event violation match-all
    10 class always do-until-failure
     10 restrict
   event authorization-failure match-all
    10 class AUTHC_SUCCESS-AUTHZ_FAIL do-until-failure
     10 authentication-restart 60
  !
  {# Open 1X then MAB Template #}
  policy-map type control subscriber PMAP_DefaultWiredDot1xOpenAuth_1X_MAB
   event session-started match-all
    10 class always do-until-failure
     10 authenticate using dot1x retries 2 retry-time 0 priority 10
   event authentication-failure match-first
    5 class DOT1X_FAILED do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    10 class AAA_SVR_DOWN_UNAUTHD_HOST do-until-failure
     30 authorize
     40 pause reauthentication
    20 class AAA_SVR_DOWN_AUTHD_HOST do-until-failure
     10 pause reauthentication
     20 authorize
    30 class DOT1X_NO_RESP do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    40 class MAB_FAILED do-until-failure
     10 terminate mab
     20 authentication-restart 60
    50 class DOT1X_TIMEOUT do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    60 class always do-until-failure
     10 terminate dot1x
     20 terminate mab
     30 authentication-restart 60
   event aaa-available match-all
    10 class IN_CRITICAL_AUTH do-until-failure
     10 clear-session
    20 class NOT_IN_CRITICAL_AUTH do-until-failure
     10 resume reauthentication
   event agent-found match-all
    10 class always do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
   event inactivity-timeout match-all
    10 class always do-until-failure
     10 clear-session
   event authentication-success match-all
   event violation match-all
    10 class always do-until-failure
     10 restrict
   event authorization-failure match-all
    10 class AUTHC_SUCCESS-AUTHZ_FAIL do-until-failure
     10 authentication-restart 60
  !
  {# Open MAB then 1X Template #}
  policy-map type control subscriber PMAP_DefaultWiredDot1xOpenAuth_MAB_1X
   event session-started match-all
    10 class always do-until-failure
     10 authenticate using mab priority 20
   event authentication-failure match-first
    5 class DOT1X_FAILED do-until-failure
     10 terminate dot1x
     20 authentication-restart 60
    10 class AAA_SVR_DOWN_UNAUTHD_HOST do-until-failure
     30 authorize
     40 pause reauthentication
    20 class AAA_SVR_DOWN_AUTHD_HOST do-until-failure
     10 pause reauthentication
     20 authorize
    30 class MAB_FAILED do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
    40 class DOT1X_NO_RESP do-until-failure
     10 terminate dot1x
     20 authentication-restart 60
    50 class DOT1X_TIMEOUT do-until-failure
     10 terminate dot1x
     20 authenticate using mab priority 20
    60 class always do-until-failure
     10 terminate mab
     20 terminate dot1x
     30 authentication-restart 60
   event aaa-available match-all
    10 class IN_CRITICAL_AUTH do-until-failure
     10 clear-session
    20 class NOT_IN_CRITICAL_AUTH do-until-failure
     10 resume reauthentication
   event agent-found match-all
    10 class always do-until-failure
     10 terminate mab
     20 authenticate using dot1x retries 2 retry-time 0 priority 10
   event inactivity-timeout match-all
    10 class always do-until-failure
     10 clear-session
   event authentication-success match-all
   event violation match-all
    10 class always do-until-failure
     10 restrict
   event authorization-failure match-all
    10 class AUTHC_SUCCESS-AUTHZ_FAIL do-until-failure
     10 authentication-restart 60
  !
  {# CTS SGACL Enforcement #}
  cts role-based enforcement
  {% macro configure_cts(vlanpairs) %}
    cts role-based enforcement vlan-list 1,{{ vlanpairs|join(',', attribute='vlan') }}
  {% endmacro %} 
```

The **macro** `configure_cts(vlanpairs)` uses the already mentioned vlan array allows us to enable the r**ole-based enforcment** via a vlan list for SGACL's

We will define a set of **macros** to drive the interface template deployment across the access switch. These templates will be logically assigned to the interfaces using a **Change of Authorization (CoA)** RADIUS message returned to the switch.

```J2
  {# IBNS2.0 Macro Section #}
  {# Interface Base Configuration IBNS2.0 Template Macro #}
  {% macro ibns_baseconf_interface() %}
    description BASE CONFIG
    switchport mode access
    snmp trap mac-notification change added
    snmp trap mac-notification change removed
    spanning-tree portfast
    spanning-tree bpduguard enable
    source template BASE_IBNS
  {% endmacro %}
  !
  {# Interface Access Point IBNS2.0 Template Macro #}
  {% macro ibns_accesspoint(vlan_number) %} 
    template ACCESS_POINT_IBNS
     description Access Point Interface
     switchport access vlan {{ vlan_number }}
     dot1x pae authenticator
     dot1x timeout supp-timeout 7
     dot1x max-req 3
     mab
     access-session port-control auto
     authentication periodic
     authentication timer reauthenticate server
     {#ip access-group ACL-DEFAULT in#}
     service-policy type control subscriber PMAP_DefaultWiredDot1xClosedAuth_MAB_1X
  {% endmacro %}
  !
  {# Interface FLex-Access Point IBNS2.0 Template Macro #}
  {% macro ibns_flexaccesspoint(vlan_number, data_number, voice_number, guest_number) %} 
    template FLEX_ACCESS_POINT_IBNS
     description Flex Access Point Interface
     switchport mode trunk
     switchport trunk native vlan {{ vlan_number }}
     switchport trunk allowed vlan {{ vlan_number }},{{ data_number }},{{ voice_number}},{{ guest_number }}
     dot1x pae authenticator
     dot1x timeout supp-timeout 7
     dot1x max-req 3
     mab
     access-session interface-template sticky timer 30
     access-session port-control auto
     authentication periodic
     authentication timer reauthenticate server
     {#ip access-group ACL-DEFAULT in#}
     service-policy type control subscriber PMAP_DefaultWiredDot1xClosedAuth_MAB_1X
  {% endmacro %}
  !
  {# Interface Workstation Access IBNS2.0 Template Macro #}
  {% macro ibns_workstation(vlan_number, voice_number) %} 
    template WORKSTATION_IBNS
     description Workstation
     switchport access vlan {{ vlan_number }}
     switchport mode access
     switchport voice vlan {{ voice_number }}
     dot1x pae authenticator
     dot1x timeout supp-timeout 7
     dot1x max-req 3
     mab
     access-session closed
     access-session port-control auto
     authentication periodic
     authentication timer reauthenticate server
     service-policy type control subscriber PMAP_DefaultWiredDot1xClosedAuth_1X_MAB
  {% endmacro %}
  !
  {# Interface Guest Access IBNS2.0 Template Macro #}
  {% macro ibns_guest(vlan_number) %} 
    template GUEST_IBNS
     description Guest Interface
     switchport access vlan {{ vlan_number }}
     switchport mode access
     dot1x pae authenticator
     dot1x timeout supp-timeout 7
     dot1x max-req 3
     mab
     access-session closed
     access-session port-control auto
     authentication periodic
     authentication timer reauthenticate server
     service-policy type control subscriber PMAP_DefaultWiredDot1xClosedAuth_1X_MAB
  {% endmacro %}
  !
  {# Interface Base Configuration IBNS2.0 Template Macro #}
  {% macro ibns_baseconfig(vlan_number) %} 
    template BASE_IBNS
     description BASE CONFIG
     switchport access vlan {{ vlan_number }}
     switchport mode access
     dot1x pae authenticator
     dot1x timeout supp-timeout 7
     dot1x max-req 3
     mab
     access-session closed
     access-session port-control auto
     authentication periodic
     authentication timer reauthenticate server
     service-policy type control subscriber PMAP_DefaultWiredDot1xClosedAuth_1X_MAB
  {% endmacro %}
```
[//]: # ({% endraw %})

These will be deployed via calling each **macro** as follows:

```J2
  {# Interface Templates #}
  {{ ibns_baseconfig(vlanArray[1]) }}
  {{ ibns_accesspoint(vlanArray[1]) }}
  {{ ibns_flexaccesspoint(vlanArray[1], vlanArray[2], vlanArray[3], vlanArray[4]) }} 
  {{ ibns_workstation(vlanArray[2], vlanArray[3]) }}
  {{ ibns_guest(vlanArray[4]) }} 
```

Once deployed the interfaces will be deployed for 802.1x configuration via the interface snippet:

```J2
   {# Automatically Configure Workstation Remaining interfaces#}
   {% for interface in __interface %}
     {% if interface.interfaceType == "Physical" && interface.portName.replaceAll("(^[a-zA-Z]+).*","$1")    == "GigabitEthernet"  %}
       {% if interface.portName.replaceAll("(^[a-zA-Z]+.).*", "$1") != "GigabitEthernet0" %}
         {% if interface.portName.replaceAll("^[a-zA-Z]+(\\d+)/(\\d+)/(\\d+)", "$2") != 1 %}
           {% if interface.portName in apintlog %}
           {% else %}
             default interface {{ interface.portName }}
             interface {{ interface.portName }}
               {{ ibns_baseconf_interface() }}
           {% endif %}
         {% endif %}
       {% endif %}
     {% endif %}
   {% endfor %}
```

We loop through all the interfaces on the switch, ensuring we configuring only those starting with GigabitEthernet and negating the management interface and any that are network modules. We then ensure the interface is not in the `apintlog` array as previously configured, and if all that is true default the interface, and place a 802.1x config on it via an interface macro.

At this point the **AAA configuration** deployed via Catalyst Centers ISE integration, will work with the configuration deployed via the regular templates.

The last piece of the puzzle is being able to deploy upstream Layer 2 CTS marking for Cisco Trustsec without breaking the provisioning automation. In order to do that, we will make use of a **self-deleting EEM** which will fire 30 seconds post deployment. This will ensure provisioning completes, and ensure the SGT are propogated.

```J2
  {#- Automated Script for cts manual disruptive config -#}
  {#- This will always ensure the uplink get the cts manual for with  -#}
  {#- timed self deleting EEM script  -#}
  event manager applet POST_CTS_MANUAL authorization bypass
   event timer countdown time 30
   action 1.0 cli command "enable"
   action 1.1 cli command "config t"
   action 2.0 cli command "interface range {{ uplink_portarray|join(',') }}"
   action 2.1 cli command "cts manual"
   action 2.2 cli command "policy static sgt 2 trusted"
   action 2.3 cli command "propagate sgt"
   action 2.4 cli command "no event manager applet POST_CTS_MANUAL"
   action 2.5 cli command "end"
   action 2.6 cli command "wr"
   action 2.7 cli command "exit"
```

Now that we have defined all the various IBNS2.0 configurations on the switch, as a device comes up on an interface, the DOT1X service policy will run and policy from ISE via a **Change of Authorization (CoA)** will drive behaviour on the port for either a vlan change or interface template assignment

</details>

## Network Profile Compliance 

To exclude specific commands from compliance checks in Catalyst Center, you can use the **ignore-compliance** flags. These flags, added to your templates, tell Catalyst Center to bypass compliance checks for commands within those boundaries. Specifically, you can enclose the commands you want to omit with:

```J2
 ! @ start-ignore-compliance 
 
 ! @ end-ignore-compliance
```

Here's a breakdown:

### What is Compliance?

Catalyst Center uses templates to define the desired configuration for your network devices. It then compares the device's running configuration against these templates to ensure they are compliant. 

### Why Omit?
There might be situations where you need to make changes to a device's configuration that don't align with the template, but you still want to keep the overall compliance status in check. For example, you might need to temporarily disable a feature for testing or make a specific change that deviates from the standard configuration. 

#### How to Omit Commands

**! @ start-ignore-compliance**: This flag indicates the start of a section in the template that should be excluded from compliance checks.

**! @ end-ignore-compliance**: This flag indicates the end of the section that should be excluded from compliance checks.

Example: 

```sh
    interface GigabitEthernet1/0/1
     ! @ start-ignore-compliance
     no switchport
     ! @ end-ignore-compliance
     switchport mode trunk
     switchport trunk allowed vlan 100,200
```

In this example, Catalyst Center will ignore the **no switchport** command for compliance checks. 

### Important Considerations

#### When to use:

Use ignore-compliance only for specific scenarios where a deviation from the template is necessary, but you want to maintain overall compliance. 

#### Documentation:

Refer to the official Catalyst Center documentation for the most up-to-date information on compliance features and how to use them. 

> [!IMPORTANT]
> **Feedback:** If you found this set of **labs** or **content** helpful, please fill in comments on this feedback form [give feedback](https://github.com/kebaldwi/DNAC-TEMPLATES/discussions/new?category=feedback-and-ideas).</br></br>
**Content Problems and Issues:** If you found an **issue** on the **lab** or **content** please fill in an [issue](https://github.com/kebaldwi/DNAC-TEMPLATES/issues/new) include what file, along with the issue you ran into. 

Special mention to: https://explore.cisco.com/dnac-use-cases/apache-velocity as examples and extrapolations were made using this documentation and Adam Radford and Josh Bronikowski for his help with some of the concepts discussed.

> [**Return to Main Menu**](../README.md)