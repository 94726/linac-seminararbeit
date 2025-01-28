const backendUrl = 'http://linac.local'

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
  nitro: {
    devProxy: {
      '/api/ws': {
        target: `${backendUrl}`, // the fix module doesn't strip the /api part so not necessary here
        ws: true
      },
      '/api': {
        target: `${backendUrl}/api`,
      },
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
    componentDir: './app/components/ui'
  },
  icon: {
    clientBundle: {
      scan: true
    }
  },

  devtools: { enabled: true },
})
