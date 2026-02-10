import { Image } from 'expo-image';
import { Tabs } from 'expo-router';
import React from 'react';

import { HapticTab } from '@/components/haptic-tab';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
        tabBarButton: HapticTab,
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: '홈',
          tabBarIcon: () => (
            <Image
              source={require('@/assets/images/home.png')}
              style={{ width: 28, height: 28 }}
              contentFit="contain"
            />
          ),
        }}
      />
      <Tabs.Screen
        name="chatbot"
        options={{
          title: '챗봇',
          tabBarIcon: () => (
            <Image
              source={require('@/assets/images/bot.png')}
              style={{ width: 28, height: 28 }}
              contentFit="contain"
            />
          ),
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: '히스토리',
          tabBarIcon: () => (
            <Image
              source={require('@/assets/images/recent.png')}
              style={{ width: 28, height: 28 }}
              contentFit="contain"
            />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: () => (
            <Image
              source={require('@/assets/images/setting.png')}
              style={{ width: 28, height: 28 }}
              contentFit="contain"
            />
          ),
        }}
      />
      <Tabs.Screen
        name="explore"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}
