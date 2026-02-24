import React from 'react';
import { Tabs } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

function PillTabBar({ state, descriptors, navigation }: any) {
  const insets = useSafeAreaInsets();

  return (
    <View
      pointerEvents="box-none"
      style={[
        styles.wrap,
        {
          bottom: insets.bottom + 36, // ← 떠있는 높이
        },
      ]}
    >
      <View style={styles.shadowShell}>
        <View style={styles.pill}>
          {state.routes.map((route: any, index: number) => {
            const isFocused = state.index === index;

            const onPress = () => {
              if (!isFocused) navigation.navigate(route.name);
            };

            let icon;
            let label;

            if (route.name === 'index') {
              icon = require('@/assets/images/home.png');
              label = '홈';
            } else if (route.name === 'history') {
              icon = require('@/assets/images/recent.png');
              label = '히스토리';
            } else if (route.name === 'mypage') {
              icon = require('@/assets/images/setting.png');
              label = '마이';
            } else {
              return null;
            }

            return (
              <Pressable
                key={route.key}
                onPress={onPress}
                style={[styles.item, isFocused && styles.itemActive]}
              >
                <Image
                  source={icon}
                  style={[
                    styles.icon,
                    { tintColor: isFocused ? '#20C14F' : '#111' },
                  ]}
                  contentFit="contain"
                />

                <Text style={[styles.label, isFocused && styles.labelActive]}>
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      tabBar={(props) => <PillTabBar {...props} />}
      screenOptions={{ headerShown: false }}
    >
      <Tabs.Screen name="index" />
      <Tabs.Screen name="history" />
      <Tabs.Screen name="mypage" />

      {/* 탭 바에 안 보이지만 라우트로 접근 가능 */}
      <Tabs.Screen name="chatbot" options={{ href: null }} />
      <Tabs.Screen name="settings" options={{ href: null }} />
      <Tabs.Screen name="explore" options={{ href: null }} />
      <Tabs.Screen name="report-history" options={{ href: null }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
  },

  shadowShell: {
    width: '90%',
    borderRadius: 999,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },

  pill: {
    height: 64,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.55)',
    flexDirection: 'row',
    alignItems: 'center',
    padding: 6,
    borderWidth: 1,
    paddingVertical: 4,
    borderColor: 'rgba(0,0,0,0.05)',
  },

  item: {
    flex: 1,
    height: '100%',
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },

  itemActive: {
    backgroundColor: 'rgba(0,0,0,0.04)',
  },

  icon: {
    width: 25,
    height: 25,
  },

  label: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111',
  },

  labelActive: {
    color: '#20C14F',
  },
});