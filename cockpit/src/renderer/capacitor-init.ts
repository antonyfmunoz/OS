import { Capacitor } from '@capacitor/core'
import { fetchApi } from './api/client'

export function initCapacitor(): void {
  if (!Capacitor.isNativePlatform()) return

  import('@capacitor/status-bar').then(({ StatusBar, Style }) => {
    StatusBar.setStyle({ style: Style.Dark })
    StatusBar.setBackgroundColor({ color: '#07080a' })
  })

  import('@capacitor/keyboard').then(({ Keyboard }) => {
    Keyboard.setAccessoryBarVisible({ isVisible: false })
  })

  import('@capacitor/push-notifications').then(({ PushNotifications }) => {
    PushNotifications.requestPermissions().then((result) => {
      if (result.receive === 'granted') {
        PushNotifications.register()
      }
    })

    PushNotifications.addListener('registration', (token) => {
      fetchApi('/push/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: token.value,
          platform: Capacitor.getPlatform(),
        }),
      }).catch(() => {})
    })

    PushNotifications.addListener('pushNotificationReceived', (notification) => {
      console.log('Push received:', notification)
    })

    PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
      const url = action.notification.data?.url as string | undefined
      if (url) window.location.href = url
    })
  })
}
