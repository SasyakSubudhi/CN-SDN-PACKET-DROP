def run():
    setLogLevel('info')
    topo = DropTopo()

    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(
            name, ip='127.0.0.1', port=6633),
        switch=OVSSwitch
    )

    net.start()

    # Wait for switch to connect to POX
    import time
    time.sleep(3)

    info("\n=== Network started! ===\n")
    info("h1=10.0.0.1, h2=10.0.0.2, h3=10.0.0.3, h4=10.0.0.4\n")
    info("Rule: h1 CANNOT reach h3. All others CAN reach each other.\n\n")

    CLI(net)
    net.stop()