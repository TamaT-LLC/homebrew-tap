cask "openpath" do
  version "0.1.2"
  sha256 "d8ceea703530a09bbca888309bee4ccc6d5fc7ded959737cd2701135fa0fe4d6"

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
