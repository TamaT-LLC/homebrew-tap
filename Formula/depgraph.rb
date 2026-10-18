class Depgraph < Formula
  desc "Explainable dependency graphs for Rust, Go, TypeScript, and JavaScript"
  homepage "https://github.com/TamaT-LLC/depgraph-cli"
  license any_of: ["MIT", "Apache-2.0"]

  depends_on "node@24"

  if OS.mac?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.4/depgraph-0.6.4-aarch64-apple-darwin.tar.gz"
    sha256 "9c2bd10bfae690d5c1e183efb1e86e2a3bb5970fada457c50ce0012a7d749b62"
  elsif Hardware::CPU.arm?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.4/depgraph-0.6.4-aarch64-unknown-linux-gnu.tar.gz"
    sha256 "df8b329fd450f681fc34c1aa89994247a1f553b9a679ab6a88852cfe75a13aa3"
  else
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.4/depgraph-0.6.4-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "aaaa1e40128733bf9c5c9e5fe936c1bb658115684f73ede466227593b0e78d62"
  end

  on_macos do
    depends_on arch: :arm64
  end

  # Homebrew must not rewrite Node shebangs in checksum-verified release artifacts.
  skip_clean "libexec"

  def install
    # Supply prefix metadata so Homebrew does not move the verified package licenses.
    cp ["LICENSE-APACHE", "LICENSE-MIT"], prefix
    # Packaged workers verify the entire release tree. Preserve every byte and path.
    libexec.install Dir["*"]
    %w[depgraph depgraph-mcp].each do |name|
      (bin/name).write_env_script libexec/"bin"/name, PATH: "#{formula_opt_bin("node@24")}:$PATH"
    end
  end

  def caveats
    <<~EOS
      Go and Rust analysis use your project's existing toolchains and offline dependencies.
      MCP/compiler-precise analysis also requires the matching verified compiler pack;
      see https://github.com/TamaT-LLC/depgraph-cli#readme for setup.
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/depgraph --version")
    (testpath/"package.json").write('{"name":"brew-fixture","version":"1.0.0","type":"module"}')
    (testpath/"tsconfig.json").write('{"compilerOptions":{"strict":true},"include":["*.ts"]}')
    (testpath/"index.ts").write("export const value: number = 42;\n")
    store = testpath/"graph.sqlite"
    scan = JSON.parse(shell_output("#{bin}/depgraph --store #{store} scan #{testpath} --json"))
    assert_equal "completed", scan.fetch("status")
    assert_operator scan.dig("coverage", "files_analyzed"), :>, 0
    result = JSON.parse(shell_output("#{bin}/depgraph --store #{store} doctor --json"))
    assert_equal "verified", result.dig("release", "core_integrity")
    assert_equal "completed", result.dig("latest_attempt", "status")
    assert_equal %w[go rust web], result.fetch("workers").map { |worker| worker.fetch("adapter") }.sort
    result.fetch("workers").each { |worker| assert_equal "verified", worker.fetch("integrity") }
  end
end
