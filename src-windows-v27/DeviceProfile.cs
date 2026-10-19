using System;
using System.Collections.Generic;

namespace MintWindows;

// Visual layout presets only. These values do not identify the OS, browser,
// model or Android version, and must not be used to override User-Agent/UA-CH.
internal sealed record DeviceProfile(string Id, string Name, int Width, int Height, double ScaleFactor)
{
    public override string ToString() => $"{Name} · {Width}×{Height}";
}

internal static class DeviceProfiles
{
    // Source for entries without "(aprox.)": Chrome DevTools' public device
    // catalog, portrait screen dimensions and device-pixel-ratio, retrieved
    // 2026-10-19. Only these numeric display fields and titles were copied.
    // https://github.com/ChromeDevTools/devtools-frontend/blob/main/front_end/models/emulation/EmulatedDevices.ts
    // Foldable entries represent the closed portrait display; no hinge,
    // spanning, cutout, safe-area or physical-device behavior is simulated.
    //
    // Entries marked "(aprox.)" are representative CSS viewport/DPR choices
    // for layout preview. They are not measured browser values and are not
    // guaranteed to match a handset's display-density settings or browser UI.
    internal static IReadOnlyList<DeviceProfile> All { get; } = Array.AsReadOnly(new DeviceProfile[]
    {
        new("pixel-10", "Google Pixel 10", 412, 924, 2.625),
        new("pixel-9", "Google Pixel 9", 412, 924, 2.625),
        new("pixel-9-pro", "Google Pixel 9 Pro", 427, 952, 3),
        new("pixel-9-pro-xl", "Google Pixel 9 Pro XL", 448, 997, 3),
        new("pixel-8", "Google Pixel 8", 412, 915, 2.625),
        new("pixel-8-pro", "Google Pixel 8 Pro", 448, 997, 3),
        new("pixel-8a", "Google Pixel 8a", 412, 915, 2.625),
        new("pixel-7", "Google Pixel 7", 412, 915, 2.625),

        new("galaxy-a55", "Samsung Galaxy A55", 360, 800, 2.25),
        new("galaxy-s20-ultra", "Samsung Galaxy S20 Ultra", 412, 915, 3.5),
        new("galaxy-s8-plus", "Samsung Galaxy S8+", 360, 740, 4),
        new("galaxy-a51-a71", "Samsung Galaxy A51/71", 412, 914, 2.625),
        new("galaxy-s24-approx", "Samsung Galaxy S24 (aprox.)", 360, 780, 3),
        new("galaxy-s24-plus-approx", "Samsung Galaxy S24+ (aprox.)", 384, 832, 3.75),
        new("galaxy-s24-ultra-approx", "Samsung Galaxy S24 Ultra (aprox.)", 412, 892, 3.5),

        new("pixel-9-pro-fold", "Google Pixel 9 Pro Fold", 412, 922, 2.625),
        new("galaxy-z-fold-6", "Samsung Galaxy Z Fold 6", 412, 968, 2.625),
        new("galaxy-z-fold-5", "Samsung Galaxy Z Fold 5", 344, 882, 2.625),

        new("moto-g4", "Motorola Moto G4", 360, 640, 3),
        new("moto-g-power", "Motorola Moto G Power", 412, 823, 1.75),
        new("motorola-edge-50-approx", "Motorola Edge 50 (aprox.)", 407, 904, 3),
        new("moto-g84-approx", "Motorola Moto G84 (aprox.)", 393, 873, 2.75),

        new("xiaomi-14-approx", "Xiaomi 14 (aprox.)", 400, 890, 3),
        new("xiaomi-14-ultra-approx", "Xiaomi 14 Ultra (aprox.)", 412, 915, 3.5),
        new("redmi-note-13-pro-approx", "Xiaomi Redmi Note 13 Pro (aprox.)", 407, 904, 3),
    });

    internal static DeviceProfile? Find(string id)
    {
        foreach (var profile in All)
            if (string.Equals(profile.Id, id, StringComparison.Ordinal))
                return profile;
        return null;
    }
}
