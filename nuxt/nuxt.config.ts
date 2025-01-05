const backendUrl = 'http://192.168.178.163:8000'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  modules: [
    "@nuxtjs/tailwindcss",
    "shadcn-nuxt",
    '@vueuse/nuxt',
    '@nuxt/icon',
    '@nuxt/eslint',
    '@nuxtjs/color-mode',
  ],
  future: {
    compatibilityVersion: 4
  },
  routeRules: {
    '/api/**': {
      proxy: process.env.NODE_ENV !== "production" ? `${backendUrl}/api/**` : undefined
    },
  },
  runtimeConfig: {
    public: {
      backendUrl,
    }
  },
  components: [
    { path: '@/components', ignore: ['@/components/ui'] },
    { path: '@/components/ui', pathPrefix: false, extensions: ['.vue'] },
  ],
  ssr: false,
  shadcn: {
    // prefix: 'Ui',

    componentDir: './app/components/ui'
  },

  devtools: { enabled: true },
})