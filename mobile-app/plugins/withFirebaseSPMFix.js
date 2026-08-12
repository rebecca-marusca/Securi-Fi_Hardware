const { withDangerousMod } = require("@expo/config-plugins");
const fs = require("fs");
const path = require("path");

module.exports = function withFirebaseSPMFix(config) {
  return withDangerousMod(config, [
    "ios",
    async (config) => {
      const podfilePath = path.join(
        config.modRequest.platformProjectRoot,
        "Podfile",
      );
      let contents = fs.readFileSync(podfilePath, "utf-8");

      // Disable Firebase's SPM resolution — its SPM packages are dynamic-only,
      // which conflicts with the project's forced-static linkage.
      if (!contents.includes("$RNFirebaseDisableSPM")) {
        contents = `$RNFirebaseDisableSPM = true\n` + contents;
      }

      // These pods need modular headers to compile correctly once SPM is disabled
      // and they're resolved via CocoaPods instead.
      const modularHeaderPods = [
        `  pod 'GoogleUtilities', :modular_headers => true`,
        `  pod 'FirebaseCoreInternal', :modular_headers => true`,
        `  pod 'FirebaseAuthInterop', :modular_headers => true`,
        `  pod 'FirebaseAppCheckInterop', :modular_headers => true`,
        `  pod 'RecaptchaInterop', :modular_headers => true`,
        `  pod 'FirebaseFirestoreInternal', :modular_headers => true`,
      ].join("\n");

      if (
        !contents.includes(`pod 'GoogleUtilities', :modular_headers => true`)
      ) {
        contents = contents.replace(
          /target ['"].*['"] do\n/,
          (match) => `${match}${modularHeaderPods}\n`,
        );
      }

      fs.writeFileSync(podfilePath, contents);
      return config;
    },
  ]);
};
