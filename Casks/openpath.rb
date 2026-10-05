cask "openpath" do
  version "0.1.1"
  sha256 "3f2f1ea74b0caf721bd72af1c333bfacc1d5379c9a4ea9d16f78f894f9d60da1"

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
