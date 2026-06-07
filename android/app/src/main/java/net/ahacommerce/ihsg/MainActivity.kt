package net.ahacommerce.ihsg

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import net.ahacommerce.ihsg.databinding.ActivityMainBinding

/**
 * Thin WebView wrapper around the IHSG dashboard hosted on Streamlit Community
 * Cloud. The dashboard itself updates server-side (git push -> auto redeploy), so
 * this app almost never needs rebuilding — only if the URL in strings.xml changes.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding
    private val startUrl: String by lazy { getString(R.string.dashboard_url) }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        // Android 15/16 (targetSdk 36) draws the app edge-to-edge, i.e. UNDER the
        // status & navigation bars. Pad the content by the system-bar + cutout
        // insets so the page header isn't hidden behind the phone's status bar.
        ViewCompat.setOnApplyWindowInsetsListener(b.root) { v, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
            )
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }

        val web = b.web
        web.setBackgroundColor(Color.parseColor("#07070B"))

        // Persist cookies so Streamlit Cloud's login/auth handshake (which bounces
        // via share.streamlit.io and back) completes INSIDE the WebView.
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true)

        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            loadWithOverviewMode = true
            useWideViewPort = true
            mediaPlaybackRequiresUserGesture = false
            offscreenPreRaster = true   // smoother scrolling (fewer white tiles)
            // Keep the default mobile user-agent so Streamlit serves its mobile layout.
        }

        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest,
            ): Boolean {
                val url = request.url
                val scheme = url.scheme ?: ""
                // Keep ALL web navigation inside the app — including Streamlit
                // Cloud's auth redirects through share.streamlit.io — so it never
                // bounces out to Chrome. Only non-web schemes go to the system.
                if (scheme == "http" || scheme == "https") return false
                // mailto:, tel:, intent:, etc. -> hand off to the system.
                openExternally(url)
                return true
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                b.swipe.isRefreshing = false
            }
        }

        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                b.progress.progress = newProgress
                b.progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
            }
        }

        // Reports (Decision Helper / Daily Trading .md) and other http(s) downloads
        // hand off to the system so the user can save/share them.
        web.setDownloadListener { url, _, _, _, _ ->
            if (url.startsWith("http")) openExternally(Uri.parse(url))
        }

        // Pull-to-refresh is disabled: an accidental pull while scrolling back up
        // to the top was reloading the page — which starts a fresh Streamlit
        // session and forced a re-login. Refresh data with the in-app sidebar
        // "Refresh" button instead.
        b.swipe.isEnabled = false

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (web.canGoBack()) web.goBack() else finish()
            }
        })

        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState)
        } else {
            web.loadUrl(startUrl)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        b.web.saveState(outState)
    }

    private fun openExternally(uri: Uri) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        } catch (_: Exception) {
            // No app to handle this URI — ignore silently.
        }
    }
}
