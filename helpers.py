import os
import platform
import sys
import xml.etree.ElementTree as XMLParser
import shutil
from fuzzywuzzy import fuzz


def scanner(cli_parsed):
    # This function was developed by Rohan Vazarkar, and then I slightly
    # modified it to fit.  Thanks for writing this man.
    ports = [80, 443, 8080, 8443]

    # Create a list of all identified web servers
    live_webservers = []

    # Define the timeout limit
    timeout = 5

    scanner_output_path = join(output_obj.eyewitness_path, "scanneroutput.txt")

    # Write out the live machine to same path as EyeWitness
    try:
        ip_range = IPNetwork(cidr_range)
        socket.setdefaulttimeout(timeout)

        for ip_to_scan in ip_range:
            ip_to_scan = str(ip_to_scan)
            for port in ports:
                print "[*] Scanning " + ip_to_scan + " on port " + str(port)
                result = checkHostPort(ip_to_scan, port)
                if (result == 0):
                    # port is open, add to the list
                    if port is 443:
                        add_to_list = "https://" + ip_to_scan + ":" + str(port)
                    else:
                        add_to_list = "http://" + ip_to_scan + ":" + str(port)
                    print "[*] Potential live webserver at " + add_to_list
                    live_webservers.append(add_to_list)
                else:
                    if (result == 10035 or result == 10060):
                        # Host is unreachable
                        pass

    except KeyboardInterrupt:
        print "[*] Scan interrupted by you rage quitting!"
        print "[*] Writing out live web servers found so far..."

    # Write out the live machines which were found so far
    for live_computer in live_webservers:
        with open(scanner_output_path, 'a') as scanout:
            scanout.write("{0}{1}".format(live_computer, os.linesep))

    frmt_str = "List of live machines written to: {0}"
    print frmt_str.format(scanner_output_path)
    sys.exit()


def target_creator(command_line_object):

    if command_line_object.createtargets is not None:
        print "Creating text file containing all web servers..."

    urls = []
    rdp = []
    vnc = []
    num_urls = 0
    try:
        # Setup variables
        # The nmap xml parsing code was sent to me and worked on by Jason Hill
        # (@jasonhillva)
        http_ports = [80, 8000, 8080, 8081, 8082, 8888]
        https_ports = [443, 8443, 9443]
        rdp_ports = [3389]
        vnc_ports = [5900, 5901]

        try:
            xml_tree = XMLParser.parse(command_line_object.f)
        except IOError:
            print "Error: EyeWitness needs a text or XML file to parse URLs!"
            sys.exit()
        root = xml_tree.getroot()

        if root.tag.lower() == "nmaprun" and root.attrib.get('scanner') == 'nmap':
            print "Detected nmap xml file\n"
            for item in root.iter('host'):
                check_ip_address = False
                # We only want hosts that are alive
                if item.find('status').get('state') == "up":
                    web_ip_address = None
                    # If there is no hostname then we'll set the IP as the
                    # target 'hostname'
                    if item.find('hostnames/hostname') is not None and command_line_object.no_dns is False:
                        target = item.find('hostnames/hostname').get('name')
                        web_ip_address = item.find('address').get('addr')
                    else:
                        target = item.find('address').get('addr')
                    # find open ports that match the http/https port list or
                    # have http/https as a service
                    for ports in item.iter('port'):
                        if ports.find('state').get('state') == 'open':
                            port = ports.attrib.get('portid')
                            try:
                                service = ports.find('service').get('name')\
                                    .lower()
                            except AttributeError:
                                # This hits when it finds an open port, but
                                # isn't able to Determine the name of the
                                # service running on it, so we'll just
                                # pass in this instance
                                pass
                            try:
                                tunnel = ports.find('service').get('tunnel')\
                                    .lower()
                            except AttributeError:
                                # This hits when it finds an open port, but
                                # isn't able to Determine the name of the
                                # service running on it, so we'll just pass
                                # in this instance
                                tunnel = "fakeportservicedoesntexist"
                            if int(port) in http_ports or 'http' in service:
                                protocol = 'http'
                                if int(port) in https_ports or 'https' in\
                                        service or ('http' in service and
                                                    'ssl' in tunnel):
                                    protocol = 'https'
                                urlBuild = '%s://%s:%s' % (protocol, target,
                                                           port)
                                if urlBuild not in urls:
                                    urls.append(urlBuild)
                                    num_urls += 1
                                else:
                                    check_ip_address = True

                            if command_line_object.rdp:
                                if int(port) in rdp_ports or 'ms-wbt' in service:
                                    rdp.append(target)

                            if command_line_object.vnc:
                                if int(port) in vnc_ports or 'vnc' in services:
                                    vnc.append((target, port))

                        if check_ip_address:
                            if int(port) in http_ports or 'http' in service:
                                protocol = 'http'
                                if int(port) in https_ports or 'https' in\
                                        service or ('http' in service and
                                                    'ssl' in tunnel):
                                    protocol = 'https'
                                if web_ip_address is not None:
                                    urlBuild = '%s://%s:%s' % (
                                        protocol, web_ip_address, port)
                                else:
                                    urlBuild = '%s://%s:%s' % (
                                        protocol, target, port)
                                if urlBuild not in urls:
                                    urls.append(urlBuild)
                                    num_urls += 1

            if command_line_object.createtargets is not None:
                with open(command_line_object.createtargets, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + command_line_object.createtargets + ").\n"
                sys.exit()
            return urls, rdp, vnc

        # Added section for parsing masscan xml output which is "inspired by"
        # but not identical to the nmap format. Based on existing code above
        # for nmap xml files. Also added check for "scanner" attribute to
        # differentiate between a file from nmap and a file from masscan.

        if root.tag.lower() == "nmaprun" and root.attrib.get('scanner') == 'masscan':
            print "Detected masscan xml file\n"
            for item in root.iter('host'):
                check_ip_address = False
                # Masscan only includes hosts that are alive, so less checking
                # needed.
                web_ip_address = None
                target = item.find('address').get('addr')
                # find open ports that match the http/https port list or
                # have http/https as a service
                for ports in item.iter('port'):
                    if ports.find('state').get('state') == 'open':
                        port = ports.attrib.get('portid')

                        # Check for http ports
                        if int(port) in http_ports:
                            protocol = 'http'
                            urlBuild = '%s://%s:%s' % (
                                protocol, target, port)
                            if urlBuild not in urls:
                                urls.append(urlBuild)

                        # Check for https ports
                        if int(port) in https_ports:
                            protocol = 'https'
                            urlBuild = '%s://%s:%s' % (
                                protocol, target, port)
                            if urlBuild not in urls:
                                urls.append(urlBuild)

                        # Check for RDP
                        if int(port) in rdp_port:
                            protocol = 'rdp'
                            if target not in rdp:
                                rdp.append(target)

                        # Check for VNC
                        if int(port) in vnc_ports:
                            protocol = 'vnc'
                            if target not in vnc:
                                vnc.append(target)

            if command_line_object.createtargets is not None:
                with open(command_line_object.createtargets, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + command_line_object.createtargets + ").\n"
                sys.exit()

            return urls, rdp, vnc

        # Find root level if it is nessus output
        # This took a little bit to do, to learn to parse the nessus output.
        # There are a variety of scripts that do it, but also being able to
        # reference PeepingTom really helped.  Tim did a great job figuring
        # out how to parse this file format
        elif root.tag.lower() == "nessusclientdata_v2":
            print "Detected .Nessus file\n"
            # Find each host in the nessus report
            for host in root.iter("ReportHost"):
                name = host.get('name')
                for item in host.iter('ReportItem'):
                    service_name = item.get('svc_name')
                    plugin_name = item.get('pluginName')
                    # I had www, but later checked out PeepingTom and Tim had
                    # http? and https? for here.  Small tests of mine haven't
                    # shown those, but as he's smarter than I am, I'll add them
                    if (service_name in ['www', 'http?', 'https?'] and
                            plugin_name.lower()
                            .startswith('service detection')):
                        port_number = item.get('port')
                        # Convert essentially to a text string and then strip
                        # newlines
                        plugin_output = item.find('plugin_output').text.strip()
                        # Look to see if web page is over SSL or TLS.
                        # If so assume it is over https and prepend https,
                        # otherwise, http
                        http_output = re.search('TLS', plugin_output) or\
                            re.search('SSL', plugin_output)
                        if http_output:
                            url = "https://" + name + ":" + port_number
                        else:
                            url = "http://" + name + ":" + port_number
                        # Just do a quick check to make sure the url we are
                        # adding doesn't already exist
                        if url not in urls:
                            urls.append(url)
                            num_urls = num_urls + 1
                    elif 'vnc' in service_name and plugin_name.lower().startswith('service detection') and command_line_object.vnc:
                        port_number = item.get('port')
                        vnc.append((name, port))
                    elif 'msrdp' in service_name and plugin_name.lower().startswith('windows terminal services') and command_line_object.rdp:
                        rdp.append(name)
            if command_line_object.createtargets is not None:
                with open(command_line_object.createtargets, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + command_line_object.createtargets + ").\n"
                sys.exit()
            return urls, rdp, vnc

        else:
            print "ERROR: EyeWitness only accepts NMap XML files!"

    except XMLParser.ParseError:

        try:
            # Open the URL file and read all URLs, and reading again to catch
            # total number of websites
            with open(command_line_object.f) as f:
                all_urls = [url for url in f if url.strip()]

            # else:
            for line in all_urls:
                if line.startswith('http://') or line.startswith('https://'):
                    urls.append(line)
                elif line.startswith('rdp://'):
                    rdp.append(line[6:])
                elif line.startswith('vnc://'):
                    vnc.append(line[6:])
                else:
                    urls.append(line)
                    if command_line_object.rdp:
                        rdp.append(line)
                    if command_line_object.vnc:
                        vnc.append(line)
                num_urls += 1

            return urls, rdp, vnc

        except IOError:
            print "ERROR: You didn't give me a valid file name! I need a valid\
            file containing URLs!"
            sys.exit()


def get_ua_values(cycle_value):
    # Create the dicts which hold different user agents.
    # Thanks to Chris John Riley for having an awesome tool which I could
    # get this info from.  His tool - UAtester.py -
    # http://blog.c22.cc/toolsscripts/ua-tester/
    # Additional user agent strings came from -
    # http://www.useragentstring.com/pages/useragentstring.php

    # "Normal" desktop user agents
    desktop_uagents = {
        "MSIE9.0": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; \
            Trident/5.0)",
        "MSIE8.0": "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; \
            Trident/4.0)",
        "MSIE7.0": "Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)",
        "MSIE6.0": "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; \
            .NET CLR 2.0.50727)",
        "Chrome32.0.1667.0": "Mozilla/5.0 (Windows NT 6.2; Win64; x64) \
        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 \
        Safari/537.36",
        "Chrome31.0.1650.16": "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36\
         (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36",
        "Firefox25": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) \
        Gecko/20100101 Firefox/25.0",
        "Firefox24": "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) \
        Gecko/20100101 Firefox/24.0,",
        "Opera12.14": "Opera/9.80 (Windows NT 6.0) Presto/2.12.388 \
        Version/12.14",
        "Opera12": "Opera/12.0(Windows NT 5.1;U;en)Presto/22.9.168 \
        Version/12.00",
        "Safari5.1.7": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) \
        AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
        "Safari5.0": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) \
        AppleWebKit/533.18.1 (KHTML, like Gecko) Version/5.0 Safari/533.16"
    }

    # Miscellaneous user agents
    misc_uagents = {
        "wget1.9.1": "Wget/1.9.1",
        "curl7.9.8": "curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8 \
        (OpenSSL 0.9.6b) (ipv6 enabled)",
        "PyCurl7.23.1": "PycURL/7.23.1",
        "Pythonurllib3.1": "Python-urllib/3.1"
    }

    # Bot crawler user agents
    crawler_uagents = {
        "Baiduspider": "Baiduspider+(+http://www.baidu.com/search/spider.htm)",
        "Bingbot": "Mozilla/5.0 (compatible; \
            bingbot/2.0 +http://www.bing.com/bingbot.htm)",
        "Googlebot2.1": "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
        "MSNBot2.1": "msnbot/2.1",
        "YahooSlurp!": "Mozilla/5.0 (compatible; Yahoo! Slurp; \
            http://help.yahoo.com/help/us/ysearch/slurp)"
    }

    # Random mobile User agents
    mobile_uagents = {
        "BlackBerry": "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) \
        AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile \
        Safari/534.11+",
        "Android": "Mozilla/5.0 (Linux; U; Android 2.3.5; en-us; HTC Vision \
            Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 \
            Mobile Safari/533.1",
        "IEMobile9.0": "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS\
            7.5; Trident/5.0; IEMobile/9.0)",
        "OperaMobile12.02": "Opera/12.02 (Android 4.1; Linux; Opera \
            Mobi/ADR-1111101157; U; en-US) Presto/2.9.201 Version/12.02",
        "iPadSafari6.0": "Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) \
        AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d \
        Safari/8536.25",
        "iPhoneSafari7.0.6": "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_6 like \
            Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 \
            Mobile/11B651 Safari/9537.53"
    }

    # Web App Vuln Scanning user agents (give me more if you have any)
    scanner_uagents = {
        "w3af": "w3af.org",
        "skipfish": "Mozilla/5.0 SF/2.10b",
        "HTTrack": "Mozilla/4.5 (compatible; HTTrack 3.0x; Windows 98)",
        "nikto": "Mozilla/5.00 (Nikto/2.1.5) (Evasions:None) (Test:map_codes)"
    }

    # Combine all user agents into a single dictionary
    all_combined_uagents = dict(desktop_uagents.items() + misc_uagents.items()
                                + crawler_uagents.items() +
                                mobile_uagents.items())

    cycle_value = cycle_value.lower()

    if cycle_value == "browser":
        return desktop_uagents
    elif cycle_value == "misc":
        return misc_uagents
    elif cycle_value == "crawler":
        return crawler_uagents
    elif cycle_value == "mobile":
        return mobile_uagents
    elif cycle_value == "scanner":
        return scanner_uagents
    elif cycle_value == "all":
        return all_combined_uagents
    else:
        print "[*] Error: You did not provide the type of user agents\
         to cycle through!".replace('    ', '')
        print "[*] Error: Defaulting to desktop browser user agents."
        return desktop_uagents


def create_web_index_head(date, time):
    return ("""<html>
        <head>
        <link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>
        <title>EyeWitness Report</title>
        <script src="jquery-1.11.3.min.js"></script>
        <script type="text/javascript">
        function toggleUA(id, url){{
        idi = "." + id;
        $(idi).toggle();
        change = document.getElementById(id);
        if (change.innerHTML.indexOf("expand") > -1){{
            change.innerHTML = "Click to collapse User Agents for " + url;
        }}else{{
            change.innerHTML = "Click to expand User Agents for " + url;
        }}
        }}
        </script>
        </head>
        <body>
        <center>
        <center>Report Generated on {0} at {1}</center>""").format(date, time)


def create_table_head():
    return ("""<table border=\"1\">
        <tr>
        <th>Web Request Info</th>
        <th>Web Screenshot</th>
        </tr>""")


def create_report_toc_head(date, time):
    return ("""<html>
        <head>
        <title>EyeWitness Report Table of Contents</title>
        </head>
        <center>Report Generated on {0} at {1}</center>
        <h2>Table of Contents</h2>""").format(date, time)


def title_screen():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')
    print "#" * 80
    print "#" + " " * 34 + "EyeWitness" + " " * 34 + "#"
    print "#" * 80 + "\n"

    python_info = sys.version_info
    if python_info[0] is not 2 or python_info[1] < 7:
        print "[*] Error: Your version of python is not supported!"
        print "[*] Error: Please install Python 2.7.X"
        sys.exit()
    else:
        pass
    return


def strip_nonalphanum(string):
    todel = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
    return string.translate(None, todel)


def get_group(group, data):
    return sorted([x for x in data if x.category == group],
                  key=lambda (k): k.page_title)


def generate_toc_section(toc, toc_table, page_num, section, sectionid, item_num):
    toc += ("<li><a href=\"report_page{0}.html#{1}\">{2}</a></li>").format(
        str(page_num), sectionid, section)
    toc_table += ("<tr><td>{0}</td><td>{1}</td>").format(section,
                                                         str(item_num))
    return toc, toc_table


def sort_data_and_write(cli_parsed, data):
    grouped = []
    total_results = len(data)
    if total_results == 0:
        print '[*] No URLS specified or no screenshots taken! Exiting'
        sys.exit()
    errors = sorted([x for x in data if x.error_state is not None],
                    key=lambda (k): k.page_title)
    data[:] = [x for x in data if x.error_state is None]
    printers = get_group('printer', data)
    netdev = get_group('netdev', data)
    cms = get_group('cms', data)
    voip = get_group('voip', data)
    nas = get_group('nas', data)
    idrac = get_group('idrac', data)
    data[:] = [x for x in data if x.category is None]
    while len(data) > 0:
        test = data.pop(0)
        temp = [x for x in data if fuzz.token_sort_ratio(
            test.page_title, x.page_title) >= 70]
        temp.append(test)
        temp = sorted(temp, key=lambda (k): k.page_title)
        grouped.extend(temp)
        data[:] = [x for x in data if fuzz.token_sort_ratio(
            test.page_title, x.page_title) < 70]
    grouped.extend(errors)
    errors = sorted(errors, key=lambda (k): k.error_state)

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)
    table_head = create_table_head()
    toc = create_report_toc_head(cli_parsed.date, cli_parsed.time)
    toc += "<li><a href=\"report_page1.html#uncat\">Uncategorized</a></li>"
    toc_table = "<table border=0.5><tr>"
    pages = []
    html = u"<h2 id=\"uncat\">Uncategorized</h2>"
    i = 1
    toc_table += "<td>Uncategorized</td><td>{0}/{1}</td></tr>".format(
        str(len(grouped)), str(total_results))
    for obj in grouped:
        html += obj.create_table_html()
        if i % cli_parsed.results == 0:
            html = (web_index_head + "EW_REPLACEME" + table_head + html +
                    "</table><br>")
            pages.append(html)
            html = u""
        i += 1

    if len(cms) > 0:
        html += "<h2 id=\"cms\">Content Management Systems (CMS)</h2>"
        html += table_head
        toc, toc_table = generate_toc_section(toc, toc_table, len(
            pages) + 1, 'Content Management Systems (CMS)', 'cms', len(cms))
        for obj in cms:
            html += obj.create_table_html()
            if i % cli_parsed.results == 0:
                html = (web_index_head + "EW_REPLACEME" + html +
                        "</table><br>")
                pages.append(html)
                html = u""
            i += 1

    if len(idrac) > 0:
        html += "<h2 id=\"idrac\">iDRAC/iLO</h2>"
        html += table_head
        toc, toc_table = generate_toc_section(
            toc, toc_table, len(pages) + 1, 'iDRAC/iLO', 'idrac', len(idrac))
        for obj in idrac:
            html += obj.create_table_html()
            if i % cli_parsed.results == 0:
                html = (web_index_head + "EW_REPLACEME" + table_head + html +
                        "</table><br>")
                pages.append(html)
                html = u""
            i += 1

    if len(nas) > 0:
        html += "<h2 id=\"nas\">Network Attached Storage (NAS)</h2>"
        html += table_head
        toc, toc_table = generate_toc_section(toc, toc_table, len(
            pages) + 1, 'Network Attached Storage (NAS)', 'nas', len(idrac))
        for obj in nas:
            html += obj.create_table_html()
            if i % cli_parsed.results == 0:
                html = (web_index_head + "EW_REPLACEME" + table_head + html +
                        "</table><br>")
                pages.append(html)
                html = u""
            i += 1

    if len(netdev) > 0:
        html += "<h2 id=\"netdev\">Network Devices</h2>"
        html += table_head
        toc, toc_table = generate_toc_section(
            toc, toc_table, len(pages) + 1, 'Network Devices', 'netdev', len(idrac))
        for obj in netdev:
            html += obj.create_table_html()
            if i % cli_parsed.results == 0:
                html = (web_index_head + "EW_REPLACEME" + table_head + html +
                        "</table><br>")
                pages.append(html)
                html = u""
            i += 1

    if len(voip) > 0:
        html += "<h2 id=\"voip\">Voice/Video over IP (VoIP)</h2>"
        html += table_head
        toc, toc_table = generate_toc_section(
            toc, toc_table, len(pages) + 1, 'Voice/Video over IP', 'VoIP', len(idrac))
        for obj in voip:
            html += obj.create_table_html()
            if i % cli_parsed.results == 0:
                html = (web_index_head + "EW_REPLACEME" + table_head + html +
                        "</table><br>")
                pages.append(html)
                html = u""
            i += 1

    if len(printers) > 0:
        html += "<h2 id=\"printer\">Printers</h2>"
        html += table_head
        toc, toc_table = generate_toc_section(
            toc, toc_table, len(pages) + 1, 'Printers', 'printers', len(idrac))
        for obj in printers:
            html += obj.create_table_html()
            if i % cli_parsed.results == 0:
                html = (web_index_head + "EW_REPLACEME" + table_head + html +
                        "</table><br>")
                pages.append(html)
                html = u""
            i += 1

    toc += "</ul>"
    toc_table += "</table>"

    if html != u"":
        html = (web_index_head + "EW_REPLACEME" + table_head + html +
                            "</table><br>")
        pages.append(html)

    toc = toc + "<br><br>" + toc_table + "</html>"

    with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as table_of_contents:
        table_of_contents.write(toc)

    if len(pages) == 1:
        with open(os.path.join(cli_parsed.d, 'report_page1.html'), 'w') as f:
            f.write(pages[0].replace('EW_REPLACEME', ''))
            f.write("</body>\n</html>")
    else:
        num_pages = len(pages) + 1
        bottom_text = "\n<center><br>Links: "
        for i in range(1, num_pages):
            bottom_text += ("<a href=\"report_page{0}.html\"> Page {0}</a>").format(
                str(i))
        bottom_text += "</center>\n"
        top_text = bottom_text
        bottom_text += "</body>\n</html>"
        pages = [
            x.replace('EW_REPLACEME', top_text) + bottom_text for x in pages]

        for i in range(1, len(pages) + 1):
            with open(os.path.join(cli_parsed.d, 'report_page{0}.html'.format(str(i))), 'w') as f:
                f.write(pages[i - 1])


def create_folders_css(cli_parsed):
    css_page = """img {
    max-width:100%;
    height:auto;
    }
    #screenshot{
    max-width: 850px;
    max-height: 550px;
    display: inline-block;
    width: 850px;
    overflow:scroll;
    }
    .hide{
    display:none;
    }
    .uabold{
    font-weight:bold;
    cursor:pointer;
    background-color:green;
    }
    .uared{
    font-weight:bold;
    cursor:pointer;
    background-color:red;
    }
    """

    os.makedirs(cli_parsed.d)
    os.makedirs(os.path.join(cli_parsed.d, 'screens'))
    os.makedirs(os.path.join(cli_parsed.d, 'source'))
    shutil.copy2('bin/jquery-1.11.3.min.js', cli_parsed.d)

    with open(os.path.join(cli_parsed.d, 'style.css'), 'w') as f:
        f.write(css_page)


def default_creds_category(cli_parsed, http_object):
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'signatures.txt')
        with open(path) as sig_file:
            signatures = sig_file.readlines()

        # Loop through and see if there are any matches from the source code
        # EyeWitness obtained
        for sig in signatures:
            # Find the signature(s), split them into their own list if needed
            # Assign default creds to its own variable
            sig_cred = sig.split('|')
            page_sig = sig_cred[0].split(";")
            cred_info = sig_cred[1]
            category = sig_cred[2]
            if category == 'none':
                category = None

            # Set our variable to 1 if the signature was not identified.  If it is
            # identified, it will be added later on.  Find total number of
            # "signatures" needed to uniquely identify the web app
            sig_not_found = 0
            # signature_range = len(page_sig)

            # This is used if there is more than one "part" of the
            # web page needed to make a signature Delimete the "signature"
            # by ";" before the "|", and then have the creds after the "|"
            for individual_signature in page_sig:
                if str(http_object.source_code).lower().find(
                        individual_signature.lower()) is not -1:
                    pass
                else:
                    sig_not_found = 1

            # If the signature was found, return the creds
            if sig_not_found == 0:
                http_object.default_creds = cred_info
                http_object.category = category
                return http_object

        http_object.default_creds = None
        http_object.category = None
        return http_object
    except IOError:
        print ('[*] WARNING: Credentials file not in the same directory\
            as EyeWitness')
        print '[*] Skipping credential check'
        return http_object
