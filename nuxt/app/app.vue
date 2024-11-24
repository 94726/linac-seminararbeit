<script setup lang="ts">
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, LinearScale, LineElement, CategoryScale, PointElement, type LineOptions, type ChartOptions, type ChartData, type ChartDataset } from 'chart.js'
ChartJS.register(Title, Tooltip, Legend, LineElement, LinearScale, CategoryScale, PointElement)
import colors from 'tailwindcss/colors'

const driftTubeAmount = 10

const { backendUrl } = useRuntimeConfig().public
const ws = useWebSocket(`${backendUrl.replace('http', 'ws')}/ws`, { autoReconnect: true })

const voltageData = ref(genVoltageData(0, driftTubeAmount))
const ldrTimings = ref([])

const chartData = computed(() => ({
  labels: Array.from({ length: driftTubeAmount }, (_, i) => `D${i + 1}`),
  datasets: [{
    stepped: 'middle',
    data: voltageData.value,
    borderColor: ws.status.value == 'OPEN' ? colors.slate[500] : undefined,
    backgroundColor: ws.status.value == 'OPEN' ? colors.slate[700] : undefined
  } satisfies ChartDataset<'line'>
  ]
}))

let chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      enabled: false,
    }
  },
  animation: {
    duration: 750,
  },
  scales: {
    y: {
      display: false,
      min: -1.1,
      max: 1.1,
    },
    x: {
      position: 'center',
    }
  }
} satisfies ChartOptions

function genVoltageData(firstVoltage: number, len: number) {
  return Array(len).fill(0).map((_, index) => index % 2 == 0 ? firstVoltage : -firstVoltage)
}

watch(ws.data, (_data) => {
  const data = JSON.parse(_data)
  if ('firstVoltage' in data) {
    voltageData.value = genVoltageData(data.firstVoltage, 10)
  }
  if ('controlMode' in data) {
    controlMode.value = data.controlMode
  }
})

async function turnVoltage() {
  await $fetch('/api/control/turn', { method: 'post' })
}

async function startLDR() {
  // TODO
  // $fetch('/api/control/start-ldr', { method: 'post' })
}

async function reset() {
  await $fetch('/api/control/reset', { method: 'post' })
}

async function updateControlMode(_controlMode: ControlMode) {
  await $fetch('/api/configuration', {
    method: 'post',
    body: { controlMode: _controlMode }
  })
  controlMode.value = _controlMode
}

type ControlMode = 'manual' | 'automatic'

const controlMode = ref<ControlMode>('manual')
</script>

<template>
  <div class="bg-muted h-dvh md:grid place-center">
    <div class="md:px-8 m-auto max-w-[1320px]">
      <section>
        <Card
          class="p-4 md:p-8 justify-center gap-6 rounded-lg flex flex-col md:grid md:grid-cols-[1fr_2fr] place-items-stretch">
          <div class="flex flex-col gap-6">
            <Card>
              <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle class="text-sm font-medium">
                  Verbindungsstatus
                </CardTitle>
                <div class="size-5 *:size-5">
                  <Transition name="fade">
                    <Icon v-if="ws.status.value == 'OPEN'" name="uil:wifi" class="absolute text-emerald-500" />
                    <Icon v-else name="uil:wifi-slash" class="absolute text-rose-500" />
                  </Transition>
                </div>
              </CardHeader>
              <CardContent>
                <div class="text-2xl font-bold">
                  <template v-if="ws.status.value == 'OPEN'">
                    Verbunden
                  </template>
                  <template v-else>
                    Verbindungsfehler
                  </template>
                </div>
                <p class="text-xs text-muted-foreground">
                  <template v-if="ws.status.value == 'OPEN'">
                  </template>
                  <template v-else>
                    Konnnte keine Verbindung aufbauen
                  </template>
                </p>
              </CardContent>
            </Card>
            <Card class="flex-1">
              <CardHeader>
                <CardTitle>Modus Konfigurieren</CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs :model-value="controlMode" @update:model-value="(v) => updateControlMode(v as never)">
                  <TabsList class="grid w-full grid-cols-2">
                    <TabsTrigger value="manual">
                      Manuell
                    </TabsTrigger>
                    <TabsTrigger value="automatic">
                      Automatisch
                    </TabsTrigger>
                  </TabsList>
                  <TabsContent value="manual" class="flex flex-col gap-2">
                    <CardDescription>
                      Erlaubt manuelle Steuerung auf Knopfdruck
                    </CardDescription>
                    <Button @click="turnVoltage">Spannung Umkehren</Button>
                    <Button variant="outline" @click="reset">Reset</Button>
                  </TabsContent>
                  <TabsContent value="automatic" class="flex flex-col gap-2">
                    <CardDescription>
                      Vollautomatische Steuerung mittels Lichtschranken
                    </CardDescription>
                    <Button @click="startLDR">Starten</Button>
                    <Button variant="outline" @click="reset">Reset</Button>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>

          <div class="grid transition-all h-[400px]" :class="{
            'grid-rows-[1fr_0fr] gap-0': controlMode == 'manual',
            'grid-rows-[1fr_1fr] gap-6': controlMode == 'automatic',
          }">
            <Card class="overflow-hidden flex flex-col">
              <CardHeader>
                <CardTitle>Spannung</CardTitle>
              </CardHeader>
              <CardContent class="relative overflow-hidden flex-1">
                <Line class="max-h-full" :data="chartData" :options="chartOptions" />
              </CardContent>
            </Card>
            <div class="overflow-hidden">
              <Card class="overflow-hidden h-full">
                <CardHeader>
                  <CardTitle>
                    Lichtschranken-Aktivierungszeiten
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>

                        </TableHead>
                        <TableHead v-for="i in driftTubeAmount" :key="i">
                          {{ `D${i}` }}
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell class="font-medium whitespace-nowrap">
                          t in s
                        </TableCell>
                        <TableCell v-for="time in ldrTimings" :key="time">{{ time }}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </div>
        </Card>
      </section>
    </div>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

