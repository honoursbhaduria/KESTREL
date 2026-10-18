import type { PlanData } from "~/api/client"

export const FIXTURE_2BHK: PlanData = {
  "units": "mm",
  "levels": [
    {
      "id": "lvl-ground",
      "name": "Ground Floor",
      "elevation_mm": 0,
      "floor_to_floor_mm": 3000,
      "rooms": [
        {
          "id": "room-living",
          "type": "living",
          "name": "Living & Dining",
          "polygon": [
            [0, 0],
            [6000, 0],
            [6000, 5000],
            [0, 5000]
          ]
        },
        {
          "id": "room-kitchen",
          "type": "kitchen",
          "name": "Kitchen",
          "polygon": [
            [6000, 0],
            [10000, 0],
            [10000, 3500],
            [6000, 3500]
          ]
        },
        {
          "id": "room-bath",
          "type": "bathroom",
          "name": "Common Bath",
          "polygon": [
            [6000, 3500],
            [10000, 3500],
            [10000, 5000],
            [6000, 5000]
          ]
        },
        {
          "id": "room-bed1",
          "type": "bedroom",
          "name": "Master Bedroom",
          "polygon": [
            [0, 5000],
            [5000, 5000],
            [5000, 10000],
            [0, 10000]
          ]
        },
        {
          "id": "room-bed2",
          "type": "bedroom",
          "name": "Guest Bedroom",
          "polygon": [
            [5000, 5000],
            [10000, 5000],
            [10000, 10000],
            [5000, 10000]
          ]
        }
      ],
      "walls": [
        {
          "id": "wall-ext-south-1",
          "start": [0, 0],
          "end": [6000, 0],
          "thickness_mm": 200,
          "height_mm": 3000,
          "is_external": true
        },
        {
          "id": "wall-ext-south-2",
          "start": [6000, 0],
          "end": [10000, 0],
          "thickness_mm": 200,
          "height_mm": 3000,
          "is_external": true
        },
        {
          "id": "wall-ext-east-1",
          "start": [10000, 0],
          "end": [10000, 5000],
          "thickness_mm": 200,
          "height_mm": 3000,
          "is_external": true
        },
        {
          "id": "wall-ext-east-2",
          "start": [10000, 5000],
          "end": [10000, 10000],
          "thickness_mm": 200,
          "height_mm": 3000,
          "is_external": true
        },
        {
          "id": "wall-ext-north",
          "start": [10000, 10000],
          "end": [0, 10000],
          "thickness_mm": 200,
          "height_mm": 3000,
          "is_external": true
        },
        {
          "id": "wall-ext-west",
          "start": [0, 10000],
          "end": [0, 0],
          "thickness_mm": 200,
          "height_mm": 3000,
          "is_external": true
        },
        {
          "id": "wall-int-h-mid",
          "start": [0, 5000],
          "end": [10000, 5000],
          "thickness_mm": 100,
          "height_mm": 3000,
          "is_external": false
        },
        {
          "id": "wall-int-v-mid",
          "start": [5000, 5000],
          "end": [5000, 10000],
          "thickness_mm": 100,
          "height_mm": 3000,
          "is_external": false
        },
        {
          "id": "wall-int-v-kitchen",
          "start": [6000, 0],
          "end": [6000, 5000],
          "thickness_mm": 100,
          "height_mm": 3000,
          "is_external": false
        },
        {
          "id": "wall-int-h-bath",
          "start": [6000, 3500],
          "end": [10000, 3500],
          "thickness_mm": 100,
          "height_mm": 3000,
          "is_external": false
        }
      ],
      "openings": [
        {
          "id": "open-main-door",
          "wall_id": "wall-ext-south-1",
          "kind": "door",
          "offset_mm": 1000,
          "width_mm": 1000,
          "height_mm": 2100,
          "sill_mm": 0,
          "swing": "inward_right"
        },
        {
          "id": "open-living-window",
          "wall_id": "wall-ext-south-1",
          "kind": "window",
          "offset_mm": 2500,
          "width_mm": 2600,
          "height_mm": 1500,
          "sill_mm": 900
        },
        {
          "id": "open-kitchen-door",
          "wall_id": "wall-int-v-kitchen",
          "kind": "door",
          "offset_mm": 1000,
          "width_mm": 900,
          "height_mm": 2100,
          "sill_mm": 0,
          "swing": "inward_left"
        },
        {
          "id": "open-kitchen-window",
          "wall_id": "wall-ext-east-1",
          "kind": "window",
          "offset_mm": 1000,
          "width_mm": 1500,
          "height_mm": 1200,
          "sill_mm": 1000
        },
        {
          "id": "open-bath-door",
          "wall_id": "wall-int-v-kitchen",
          "kind": "door",
          "offset_mm": 3800,
          "width_mm": 800,
          "height_mm": 2100,
          "sill_mm": 0,
          "swing": "inward_left"
        },
        {
          "id": "open-bed1-door",
          "wall_id": "wall-int-h-mid",
          "kind": "door",
          "offset_mm": 1500,
          "width_mm": 900,
          "height_mm": 2100,
          "sill_mm": 0,
          "swing": "inward_left"
        },
        {
          "id": "open-bed1-window",
          "wall_id": "wall-ext-north",
          "kind": "window",
          "offset_mm": 6500,
          "width_mm": 2200,
          "height_mm": 1500,
          "sill_mm": 900
        },
        {
          "id": "open-bed2-door",
          "wall_id": "wall-int-h-mid",
          "kind": "door",
          "offset_mm": 7000,
          "width_mm": 900,
          "height_mm": 2100,
          "sill_mm": 0,
          "swing": "inward_right"
        },
        {
          "id": "open-bed2-window",
          "wall_id": "wall-ext-north",
          "kind": "window",
          "offset_mm": 1500,
          "width_mm": 2200,
          "height_mm": 1500,
          "sill_mm": 900
        }
      ],
      "stairs": []
    }
  ]
}


export const FIXTURE_3BHK: PlanData = {
  "units": "mm",
  "levels": [
    {
      "id": "lvl-ground",
      "name": "Ground Level",
      "elevation_mm": 0,
      "floor_to_floor_mm": 3200,
      "rooms": [
        {
          "id": "room-g-living",
          "type": "living",
          "name": "Grand Foyer & Living",
          "polygon": [
            [0, 0],
            [7000, 0],
            [7000, 6000],
            [0, 6000]
          ]
        },
        {
          "id": "room-g-kitchen",
          "type": "kitchen",
          "name": "Gourmet Kitchen",
          "polygon": [
            [7000, 0],
            [12000, 0],
            [12000, 4000],
            [7000, 4000]
          ]
        },
        {
          "id": "room-g-powder",
          "type": "bathroom",
          "name": "Powder Room",
          "polygon": [
            [7000, 4000],
            [9500, 4000],
            [9500, 6000],
            [7000, 6000]
          ]
        },
        {
          "id": "room-g-stairwell",
          "type": "corridor",
          "name": "Stairwell Hall",
          "polygon": [
            [9500, 4000],
            [12000, 4000],
            [12000, 6000],
            [9500, 6000]
          ]
        },
        {
          "id": "room-g-bed1",
          "type": "bedroom",
          "name": "Guest Suite",
          "polygon": [
            [0, 6000],
            [6000, 6000],
            [6000, 11000],
            [0, 11000]
          ]
        }
      ],
      "walls": [
        {
          "id": "wall-g-south",
          "start": [0, 0],
          "end": [12000, 0],
          "thickness_mm": 230,
          "height_mm": 3200,
          "is_external": true
        },
        {
          "id": "wall-g-east",
          "start": [12000, 0],
          "end": [12000, 6000],
          "thickness_mm": 230,
          "height_mm": 3200,
          "is_external": true
        },
        {
          "id": "wall-g-north",
          "start": [12000, 6000],
          "end": [0, 6000],
          "thickness_mm": 115,
          "height_mm": 3200,
          "is_external": false
        },
        {
          "id": "wall-g-west",
          "start": [0, 6000],
          "end": [0, 0],
          "thickness_mm": 230,
          "height_mm": 3200,
          "is_external": true
        }
      ],
      "openings": [
        {
          "id": "open-g-main-door",
          "wall_id": "wall-g-south",
          "kind": "door",
          "offset_mm": 1500,
          "width_mm": 1100,
          "height_mm": 2400,
          "sill_mm": 0,
          "swing": "inward_right"
        }
      ],
      "stairs": [
        {
          "id": "stair-main",
          "polygon": [
            [9500, 4000],
            [12000, 4000],
            [12000, 6000],
            [9500, 6000]
          ],
          "riser_mm": 160,
          "tread_mm": 280,
          "direction": "up"
        }
      ]
    },
    {
      "id": "lvl-first",
      "name": "First Floor",
      "elevation_mm": 3200,
      "floor_to_floor_mm": 3000,
      "rooms": [
        {
          "id": "room-f-master",
          "type": "bedroom",
          "name": "Master Suite",
          "polygon": [
            [0, 0],
            [6000, 0],
            [6000, 6000],
            [0, 6000]
          ]
        },
        {
          "id": "room-f-bed2",
          "type": "bedroom",
          "name": "Kids Bedroom",
          "polygon": [
            [6000, 0],
            [12000, 0],
            [12000, 6000],
            [6000, 6000]
          ]
        }
      ],
      "walls": [
        {
          "id": "wall-f-south",
          "start": [0, 0],
          "end": [12000, 0],
          "thickness_mm": 230,
          "height_mm": 3000,
          "is_external": true
        },
        {
          "id": "wall-f-mid",
          "start": [6000, 0],
          "end": [6000, 6000],
          "thickness_mm": 115,
          "height_mm": 3000,
          "is_external": false
        }
      ],
      "openings": [],
      "stairs": []
    }
  ]
}


export const FIXTURE_VIOLATIONS: PlanData = {
  "units": "mm",
  "levels": [
    {
      "id": "lvl-ground",
      "name": "Ground Level",
      "elevation_mm": 0,
      "floor_to_floor_mm": 2400,
      "rooms": [
        {
          "id": "room-bed-small",
          "type": "bedroom",
          "name": "Tiny Study Bed",
          "polygon": [
            [0, 0],
            [2500, 0],
            [2500, 2000],
            [0, 2000]
          ]
        },
        {
          "id": "room-kitchen-narrow",
          "type": "kitchen",
          "name": "Narrow Galley Kitchen",
          "polygon": [
            [2500, 0],
            [3900, 0],
            [3900, 4000],
            [2500, 4000]
          ]
        },
        {
          "id": "room-outside-boundary",
          "type": "living",
          "name": "Overhanging Living Hall",
          "polygon": [
            [3900, 0],
            [25000, 0],
            [25000, 8000],
            [3900, 8000]
          ]
        }
      ],
      "walls": [
        {
          "id": "wall-v-small",
          "start": [0, 0],
          "end": [2500, 0],
          "thickness_mm": 200,
          "height_mm": 2400,
          "is_external": true
        },
        {
          "id": "wall-v-kitchen",
          "start": [2500, 0],
          "end": [2500, 4000],
          "thickness_mm": 100,
          "height_mm": 2400,
          "is_external": false
        }
      ],
      "openings": [
        {
          "id": "open-door-narrow",
          "wall_id": "wall-v-kitchen",
          "kind": "door",
          "offset_mm": 500,
          "width_mm": 650,
          "height_mm": 2000,
          "sill_mm": 0,
          "swing": "inward_left"
        },
        {
          "id": "open-win-tiny",
          "wall_id": "wall-v-small",
          "kind": "window",
          "offset_mm": 500,
          "width_mm": 400,
          "height_mm": 400,
          "sill_mm": 1000
        }
      ],
      "stairs": [
        {
          "id": "stair-steep",
          "polygon": [
            [0, 2000],
            [1500, 2000],
            [1500, 4000],
            [0, 4000]
          ],
          "riser_mm": 220,
          "tread_mm": 210,
          "direction": "up"
        }
      ]
    }
  ]
}


export const FIXTURE_OPTIONS = [
  { id: "2bhk", name: "2BHK Single Level (Clean)", data: FIXTURE_2BHK },
  { id: "3bhk", name: "3BHK Duplex (2 Levels)", data: FIXTURE_3BHK },
  { id: "violations", name: "Code Violations Fixture", data: FIXTURE_VIOLATIONS },
]
