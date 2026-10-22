class Depgraph < Formula
  desc "Explainable dependency graphs for Rust, Go, TypeScript, and JavaScript"
  homepage "https://github.com/TamaT-LLC/depgraph-cli"
  license any_of: ["MIT", "Apache-2.0"]

  depends_on "node@24"

  if OS.mac?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.2/depgraph-0.7.2-aarch64-apple-darwin.tar.gz"
    sha256 "269e4364a8fd9a7e7d3fcf74c6d8195302fe7f149dffa286500e639faa6706d4"
  elsif Hardware::CPU.arm?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.2/depgraph-0.7.2-aarch64-unknown-linux-gnu.tar.gz"
    sha256 "bef20cd34c3e3072905bbdf5288f8d7039988a08f9af60904fa3a04a32b7fcda"
  else
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.2/depgraph-0.7.2-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "58ca8a0bec00426a2e8965a9429e7eddc91f1dd89a5d01687105ab2a5e1c5dff"
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
