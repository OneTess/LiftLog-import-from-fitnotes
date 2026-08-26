import { afterEach, describe, expect, it, vi } from 'vitest';
import { Instant } from '@js-joda/core';
import * as ReactNative from 'react-native';

vi.mock('react-native-purchases', () => ({
  default: { configure: vi.fn(), getCustomerInfo: vi.fn(), syncPurchases: vi.fn() },
}));

import Purchases from 'react-native-purchases';
import { createAddEffectTestBed } from '@/utils/__test__/add-effect-testbed';
import {
  applySettingsEffects,
  maybeConfigurePurchases,
  revenueCatApiKeyForPlatform,
} from '@/store/settings/effects';
import {
  initializeSettingsStateSlice,
  setColorSchemeSeed,
  setExportToHealthAggregator,
  setIsHydrated,
  setProToken,
  settingsReducer,
} from '@/store/settings';
import { preferenceRegistry } from '@/store/settings/registry';

describe('settings slice - generated preference actions', () => {
  it('applies a generated setter through the matcher reducer', () => {
    const state = settingsReducer(undefined, setColorSchemeSeed('#abcdef'));
    expect(state.colorSchemeSeed).toBe('#abcdef');
  });

  it('keeps the historical action type string', () => {
    expect(setColorSchemeSeed('#abcdef').type).toBe('settings/setColorSchemeSeed');
  });

  it('seeds initial state from the registry defaults (drift fixed to true)', () => {
    const state = settingsReducer(undefined, { type: '@@init' });
    expect(state.notesExpandedByDefault).toBe(true);
    expect(state.keepScreenAwakeDuringWorkout).toBe(true);
    expect(state.isHydrated).toBe(false);
  });
});

function makeTestBed(isHydrated: boolean, extraServices?: Record<string, unknown>) {
  const preferenceService = {
    setPreference: vi.fn(() => Promise.resolve()),
    setProToken: vi.fn(() => Promise.resolve()),
  };
  const testBed = createAddEffectTestBed({
    initialState: { settings: { isHydrated } },
    services: { preferenceService, ...extraServices } as never,
  });
  applySettingsEffects(testBed.addEffect);
  return { testBed, preferenceService };
}

describe('settings effects - generic persistence', () => {
  it('persists a generic preference when hydrated', async () => {
    const { testBed, preferenceService } = makeTestBed(true);
    await testBed.dispatchHandled(setColorSchemeSeed('#abcdef'));
    expect(preferenceService.setPreference).toHaveBeenCalledWith('colorSchemeSeed', '#abcdef');
  });

  it('does not persist before hydration', async () => {
    const { testBed, preferenceService } = makeTestBed(false);
    await testBed.dispatchHandled(setColorSchemeSeed('#abcdef'));
    expect(preferenceService.setPreference).not.toHaveBeenCalled();
  });

  it('routes a persist:false key through its bespoke effect, not the generic one', async () => {
    const { testBed, preferenceService } = makeTestBed(true);
    await testBed.dispatchHandled(setProToken('tok'));
    expect(preferenceService.setProToken).toHaveBeenCalledWith('tok');
    expect(preferenceService.setPreference).not.toHaveBeenCalled();
  });
});

describe('maybeConfigurePurchases', () => {
  afterEach(() => {
    vi.mocked(Purchases.configure).mockReset();
  });

  it('does not call Purchases.configure when the App Store key is missing', () => {
    expect(maybeConfigurePurchases(undefined)).toBe(false);
    expect(maybeConfigurePurchases('')).toBe(false);
    expect(Purchases.configure).not.toHaveBeenCalled();
  });

  it('configures with { apiKey } when a key is present', () => {
    expect(maybeConfigurePurchases('appl_test_key')).toBe(true);
    expect(Purchases.configure).toHaveBeenCalledWith({ apiKey: 'appl_test_key' });
  });

  it('picks the iOS env key and not the Android one', () => {
    const env = {
      EXPO_PUBLIC_REVENUECAT_APPLE_API_KEY: 'appl_ios',
      EXPO_PUBLIC_REVENUECAT_GOOGLE_API_KEY: 'goog_android',
    } as NodeJS.ProcessEnv;
    expect(revenueCatApiKeyForPlatform('ios', env)).toBe('appl_ios');
    expect(revenueCatApiKeyForPlatform('android', env)).toBe('goog_android');
    expect(revenueCatApiKeyForPlatform('web', env)).toBeUndefined();
  });
});

function makeHydrationPreferenceService() {
  return {
    getPreference: vi.fn(async (key: keyof typeof preferenceRegistry) => preferenceRegistry[key].default),
    getPreferredLanguage: vi.fn(() => 'en'),
    getRemoteBackupSettings: vi.fn(async () => ({
      endpoint: '',
      apiKey: '',
      includeFeedAccount: false,
    })),
    getLastSuccessfulRemoteBackupHash: vi.fn(async () => undefined),
    getLastBackupTime: vi.fn(async () => Instant.EPOCH),
    getProToken: vi.fn(async () => undefined),
  };
}

describe('settings effects - initializeSettingsStateSlice without RevenueCat', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.mocked(Purchases.configure).mockReset();
  });

  it('still hydrates when the Release IPA has no RevenueCat key', async () => {
    vi.stubGlobal('__DEV__', false);
    Object.assign(ReactNative, { Platform: { OS: 'ios' } });
    vi.stubEnv('EXPO_PUBLIC_REVENUECAT_APPLE_API_KEY', '');
    const preferenceService = makeHydrationPreferenceService();
    const testBed = createAddEffectTestBed({
      initialState: { settings: { isHydrated: false } },
      services: { preferenceService } as never,
    });
    applySettingsEffects(testBed.addEffect);
    await testBed.dispatchHandled(initializeSettingsStateSlice());
    expect(Purchases.configure).not.toHaveBeenCalled();
    expect(testBed.getDispatchedAction(setIsHydrated).payload).toBe(true);
  });

  it('still hydrates when Purchases.configure throws Invalid API key', async () => {
    vi.stubGlobal('__DEV__', false);
    Object.assign(ReactNative, { Platform: { OS: 'ios' } });
    vi.stubEnv('EXPO_PUBLIC_REVENUECAT_APPLE_API_KEY', 'not-an-object-key');
    vi.mocked(Purchases.configure).mockImplementation(() => {
      throw new Error('Invalid API key. It must be called with an Object: configure({apiKey: "key"})');
    });
    const preferenceService = makeHydrationPreferenceService();
    const testBed = createAddEffectTestBed({
      initialState: { settings: { isHydrated: false } },
      services: { preferenceService } as never,
    });
    applySettingsEffects(testBed.addEffect);
    await testBed.dispatchHandled(initializeSettingsStateSlice());
    expect(Purchases.configure).toHaveBeenCalled();
    expect(testBed.getDispatchedAction(setIsHydrated).payload).toBe(true);
    expect(testBed.mockServices.logger.error).toHaveBeenCalled();
  });
});

describe('settings effects - exportToHealthAggregator gate', () => {
  it('reverts and does not persist when export is unavailable', async () => {
    const healthExportService = { canExport: vi.fn(() => false), requestPermission: vi.fn() };
    const { testBed, preferenceService } = makeTestBed(true, { healthExportService });
    await testBed.dispatchHandled(setExportToHealthAggregator(true));
    expect(testBed.getDispatchedAction(setExportToHealthAggregator).payload).toBe(false);
    expect(preferenceService.setPreference).not.toHaveBeenCalled();
  });
});
