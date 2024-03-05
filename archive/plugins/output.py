#!/usr/bin/env python3
#
# plugins/output.py

import json

class OutputPlugin:
    async def save(self, data):
        with open("output.json", "w") as f:
            json.dump(data, f)

output_plugin = OutputPlugin()
