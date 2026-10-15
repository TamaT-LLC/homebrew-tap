cask "openpath" do
  version "0.1.3"
  sha256 "28be63f0ae19232f5be8a53ea614cacc2d79820d57ba21e0931449fa9b9494a5"

  url "https://github.com/TamaT-LLC/openpath/releases/download/v#{version}/openpath-#{version}.zip"
  name "openpath"
  desc "Fuzzy search palette for file open dialogs"
  homepage "https://github.com/TamaT-LLC/openpath"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: :sonoma

  app "openpath.app"

  uninstall quit: "jp.tamat.openpath"

  zap trash: [
    "~/.config/openpath",
    "~/Library/Application Support/openpath",
    "~/Library/Logs/openpath",
    "~/Library/Preferences/jp.tamat.openpath.plist",
  ]
end
